#!/usr/bin/env node
/**
 * Validate the Vue i18n locale files against the English source.
 *
 * Fails (exit 1) when a target locale:
 *   - is missing keys that exist in en.js, or
 *   - has interpolation placeholders that don't match the English value
 *     (e.g. {count} present in en but missing/renamed in the translation).
 *
 * This is meant to run in CI so untranslated or broken locales are caught
 * automatically — no manual review needed.
 *
 * Usage:
 *   npm run i18n:check
 */

import { fileURLToPath, pathToFileURL } from 'node:url'
import { dirname, join } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const I18N_DIR = join(__dirname, '..', 'src', 'i18n')

const SOURCE_LANG = 'en'
const TARGETS = ['ro', 'de', 'fr', 'es', 'ru', 'uk']
const PLACEHOLDER_RE = /\{[^}]+\}/g

function isPlainObject(v) {
  return v && typeof v === 'object' && !Array.isArray(v)
}

async function loadLocale(lang) {
  const url = pathToFileURL(join(I18N_DIR, `${lang}.js`)).href
  const mod = await import(url)
  return mod.default
}

function placeholders(text) {
  return (String(text).match(PLACEHOLDER_RE) || []).sort()
}

function walk(source, target, prefix, problems) {
  for (const [key, srcVal] of Object.entries(source)) {
    const path = [...prefix, key].join('.')
    const tgtVal = target ? target[key] : undefined
    if (isPlainObject(srcVal)) {
      walk(srcVal, isPlainObject(tgtVal) ? tgtVal : undefined, [...prefix, key], problems)
    } else if (tgtVal === undefined) {
      problems.push(`missing key: ${path}`)
    } else {
      const a = placeholders(srcVal)
      const b = placeholders(tgtVal)
      if (a.join('|') !== b.join('|')) {
        problems.push(`placeholder mismatch at ${path}: en=[${a}] got=[${b}]`)
      }
    }
  }
}

async function main() {
  const source = await loadLocale(SOURCE_LANG)
  let failed = false

  for (const lang of TARGETS) {
    let target
    try {
      target = await loadLocale(lang)
    } catch (e) {
      console.error(`✗ ${lang}: cannot load (${e.message})`)
      failed = true
      continue
    }
    const problems = []
    walk(source, target, [], problems)
    if (problems.length) {
      failed = true
      console.error(`✗ ${lang}: ${problems.length} problem(s)`)
      for (const p of problems.slice(0, 40)) console.error(`    - ${p}`)
      if (problems.length > 40) console.error(`    ... and ${problems.length - 40} more`)
    } else {
      console.log(`✓ ${lang}: complete`)
    }
  }

  if (failed) {
    console.error('\ni18n check failed. Run "npm run i18n:translate" to fill missing keys.')
    process.exit(1)
  }
  console.log('\nAll locales are complete and placeholder-safe.')
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
