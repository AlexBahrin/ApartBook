#!/usr/bin/env node
/**
 * Auto-translate the Vue i18n locale files using a self-hosted LibreTranslate.
 *
 * Source of truth: src/i18n/en.js
 * Targets:         ro, de, fr, es, ru, uk
 *
 * Rules:
 *   - English (en.js) is never modified — it is the source.
 *   - Romanian (ro.js) is ADD-ONLY: existing keys are preserved exactly,
 *     only missing keys are translated and added.
 *   - Other locales: any key that is missing, still equal to the English
 *     value, or whose interpolation placeholders no longer match English is
 *     (re)translated. Real existing translations are preserved.
 *
 * Placeholders like {count}, {page}, {total} are NEVER sent to the translator.
 * The text is split around them, only the literal segments are translated, and
 * the original placeholders are re-inserted verbatim, so they always survive.
 *
 * Requirements: a running LibreTranslate instance (no Docker needed):
 *   python3.12 -m venv .venv-libretranslate
 *   .venv-libretranslate/bin/pip install libretranslate
 *   .venv-libretranslate/bin/libretranslate --host 127.0.0.1 --port 5111 \
 *       --load-only en,ro,de,fr,es,ru,uk
 *
 * Environment variables:
 *   LIBRETRANSLATE_URL      (default: http://localhost:5000)
 *   LIBRETRANSLATE_API_KEY  (optional)
 *
 * Usage:
 *   npm run i18n:translate            # all target locales
 *   npm run i18n:translate -- de fr   # only the given locales
 */

import { writeFile } from 'node:fs/promises'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { dirname, join } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const I18N_DIR = join(__dirname, '..', 'src', 'i18n')

const SOURCE_LANG = 'en'
const ALL_TARGETS = ['ro', 'de', 'fr', 'es', 'ru', 'uk']
const ADD_ONLY = new Set(['ro'])

const LT_URL = (process.env.LIBRETRANSLATE_URL || 'http://localhost:5000').replace(/\/$/, '')
const LT_API_KEY = process.env.LIBRETRANSLATE_API_KEY || ''

const PLACEHOLDER_RE = /\{[^}]+\}/g

// --- Locale file IO --------------------------------------------------------

async function loadLocale(lang) {
  const url = pathToFileURL(join(I18N_DIR, `${lang}.js`)).href
  const mod = await import(`${url}?t=${Date.now()}`)
  return mod.default
}

function isPlainObject(v) {
  return v && typeof v === 'object' && !Array.isArray(v)
}

const IDENT_RE = /^[A-Za-z_$][A-Za-z0-9_$]*$/

function serializeKey(key) {
  return IDENT_RE.test(key) ? key : `'${key.replace(/'/g, "\\'")}'`
}

function serializeString(str) {
  return `'${str.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/\n/g, '\\n')}'`
}

function serialize(obj, indent = 2) {
  const pad = ' '.repeat(indent)
  const lines = []
  for (const [key, value] of Object.entries(obj)) {
    if (isPlainObject(value)) {
      lines.push(`${pad}${serializeKey(key)}: ${serialize(value, indent + 2)},`)
    } else {
      lines.push(`${pad}${serializeKey(key)}: ${serializeString(String(value))},`)
    }
  }
  return `{\n${lines.join('\n')}\n${' '.repeat(indent - 2)}}`
}

function fileContents(obj) {
  return `export default ${serialize(obj)}\n`
}

// --- Placeholder-safe translation ------------------------------------------

function placeholders(text) {
  return (String(text).match(PLACEHOLDER_RE) || []).sort()
}

/** Split a string into literal/placeholder parts, preserving order. */
function tokenize(text) {
  const parts = []
  let last = 0
  for (const m of text.matchAll(PLACEHOLDER_RE)) {
    if (m.index > last) parts.push({ lit: text.slice(last, m.index) })
    parts.push({ ph: m[0] })
    last = m.index + m[0].length
  }
  if (last < text.length) parts.push({ lit: text.slice(last) })
  if (parts.length === 0) parts.push({ lit: '' })
  return parts
}

const WS_RE = /^(\s*)([\s\S]*?)(\s*)$/

async function libreTranslate(texts, target) {
  if (texts.length === 0) return []
  const body = { q: texts, source: SOURCE_LANG, target, format: 'text' }
  if (LT_API_KEY) body.api_key = LT_API_KEY
  const res = await fetch(`${LT_URL}/translate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(`LibreTranslate ${res.status}: ${detail.slice(0, 300)}`)
  }
  const data = await res.json()
  const out = Array.isArray(data.translatedText) ? data.translatedText : [data.translatedText]
  return out.map((t) => String(t))
}

/** Translate literal segments, keeping surrounding whitespace intact. */
async function translateSegments(segments, target) {
  const payloadTexts = []
  const meta = []
  for (const seg of segments) {
    const [, lead, core, trail] = seg.match(WS_RE)
    if (core) {
      meta.push({ lead, trail, idx: payloadTexts.length })
      payloadTexts.push(core)
    } else {
      meta.push({ raw: seg })
    }
  }
  const translatedCores = await libreTranslate(payloadTexts, target)
  return meta.map((m) => (m.raw !== undefined ? m.raw : m.lead + translatedCores[m.idx] + m.trail))
}

// --- Diffing ---------------------------------------------------------------

function collectJobs(source, existing, lang, prefix = [], jobs = []) {
  for (const [key, srcVal] of Object.entries(source)) {
    const path = [...prefix, key]
    const exVal = existing ? existing[key] : undefined
    if (isPlainObject(srcVal)) {
      collectJobs(srcVal, isPlainObject(exVal) ? exVal : undefined, lang, path, jobs)
    } else {
      const src = String(srcVal)
      let needs
      if (ADD_ONLY.has(lang)) {
        needs = exVal === undefined
      } else {
        needs =
          exVal === undefined ||
          exVal === src ||
          placeholders(src).join('|') !== placeholders(exVal).join('|')
      }
      if (needs) jobs.push({ path, source: src })
    }
  }
  return jobs
}

function setPath(obj, path, value) {
  let node = obj
  for (let i = 0; i < path.length - 1; i++) {
    const k = path[i]
    if (!isPlainObject(node[k])) node[k] = {}
    node = node[k]
  }
  node[path[path.length - 1]] = value
}

function buildResult(source, existing, translations) {
  const result = {}
  const walk = (src, ex, prefix) => {
    for (const [key, srcVal] of Object.entries(src)) {
      const path = [...prefix, key]
      const exVal = ex ? ex[key] : undefined
      if (isPlainObject(srcVal)) {
        walk(srcVal, isPlainObject(exVal) ? exVal : undefined, path)
      } else {
        const keyStr = path.join('.')
        if (translations.has(keyStr)) setPath(result, path, translations.get(keyStr))
        else if (exVal !== undefined) setPath(result, path, exVal)
        else setPath(result, path, String(srcVal))
      }
    }
  }
  walk(source, existing, [])
  return result
}

// --- Main ------------------------------------------------------------------

async function translateLocale(lang, source) {
  let existing = null
  try {
    existing = await loadLocale(lang)
  } catch {
    existing = null
  }

  const jobs = collectJobs(source, existing, lang)
  if (jobs.length === 0) {
    console.log(`  ${lang}: nothing to translate (up to date).`)
    return
  }
  console.log(`  ${lang}: translating ${jobs.length} string(s)...`)

  const translations = new Map()
  for (const job of jobs) {
    const parts = tokenize(job.source)
    const lits = parts.filter((p) => p.lit !== undefined).map((p) => p.lit)
    const translatedLits = await translateSegments(lits, lang)
    let li = 0
    const rebuilt = parts.map((p) => (p.ph !== undefined ? p.ph : translatedLits[li++])).join('')
    translations.set(job.path.join('.'), rebuilt)
  }

  const result = buildResult(source, existing, translations)
  await writeFile(join(I18N_DIR, `${lang}.js`), fileContents(result), 'utf8')
  console.log(`  ${lang}: wrote ${jobs.length} translation(s).`)
}

async function main() {
  const requested = process.argv.slice(2).filter(Boolean)
  const targets = requested.length ? requested : ALL_TARGETS

  try {
    const ping = await fetch(`${LT_URL}/languages`)
    if (!ping.ok) throw new Error(`status ${ping.status}`)
  } catch (e) {
    console.error(`\nCannot reach LibreTranslate at ${LT_URL}.`)
    console.error('Start it with:')
    console.error('  .venv-libretranslate/bin/libretranslate --host 127.0.0.1 --port 5111 --load-only en,ro,de,fr,es,ru,uk')
    console.error(`Details: ${e.message}\n`)
    process.exit(1)
  }

  const source = await loadLocale(SOURCE_LANG)
  console.log(`Translating from '${SOURCE_LANG}' via ${LT_URL}`)
  for (const lang of targets) {
    if (lang === SOURCE_LANG) continue
    await translateLocale(lang, source)
  }
  console.log('Done.')
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
