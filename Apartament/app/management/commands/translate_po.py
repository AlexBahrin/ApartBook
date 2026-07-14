"""
Auto-translate Django .po catalogs using a self-hosted LibreTranslate.

Source language: English (the msgid text).
Targets: every language in settings.LANGUAGES except English.

Rules:
  - English is the source and is never written.
  - Romanian is ADD-ONLY: only empty msgstr entries are filled; existing
    Romanian translations (including fuzzy ones) are left untouched.
  - Other languages: entries that are empty, fuzzy, or whose placeholders no
    longer match the source are (re)translated and the fuzzy flag is cleared.
    This also repairs bad machine translations.

Placeholders (%(name)s, %s, %d, {name}, {…}) are NEVER sent to the translator.
Each string is split around them, only the literal segments are translated, and
the original placeholders are re-inserted verbatim, so they always survive.

Requirements: a running LibreTranslate instance (no Docker needed):
  python3.12 -m venv .venv-libretranslate
  .venv-libretranslate/bin/pip install libretranslate
  .venv-libretranslate/bin/libretranslate --host 127.0.0.1 --port 5111 \
      --load-only en,ro,de,fr,es,ru,uk

Environment variables:
  LIBRETRANSLATE_URL      (default: http://localhost:5000)
  LIBRETRANSLATE_API_KEY  (optional)

Usage:
  python manage.py translate_po
  python manage.py translate_po --langs de fr --compile
"""

import os
import re
import json
import urllib.request

import polib
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management import call_command


SOURCE_LANG = 'en'
ADD_ONLY = {'ro'}

PLACEHOLDER_RE = re.compile(r'%\([^)]*\)[sdrefgxo]|%[sdrefgxo]|\{[^}]*\}')
WS_RE = re.compile(r'^(\s*)([\s\S]*?)(\s*)$')


def _placeholders(text):
    return sorted(PLACEHOLDER_RE.findall(text or ''))


def _tokenize(text):
    """Split into [('lit', s) | ('ph', s)] preserving order."""
    parts = []
    last = 0
    for m in PLACEHOLDER_RE.finditer(text):
        if m.start() > last:
            parts.append(('lit', text[last:m.start()]))
        parts.append(('ph', m.group(0)))
        last = m.end()
    if last < len(text):
        parts.append(('lit', text[last:]))
    if not parts:
        parts.append(('lit', ''))
    return parts


class Command(BaseCommand):
    help = 'Auto-translate Django .po files via LibreTranslate.'

    def add_arguments(self, parser):
        parser.add_argument('--langs', nargs='*', default=None,
                            help='Language codes to translate (default: all except English).')
        parser.add_argument('--compile', action='store_true',
                            help='Run compilemessages after translating.')

    def handle(self, *args, **options):
        self.lt_url = os.environ.get('LIBRETRANSLATE_URL', 'http://localhost:5000').rstrip('/')
        self.lt_key = os.environ.get('LIBRETRANSLATE_API_KEY', '')

        if not self._reachable():
            self.stderr.write(self.style.ERROR(
                f'Cannot reach LibreTranslate at {self.lt_url}. Start it with:\n'
                '  .venv-libretranslate/bin/libretranslate --host 127.0.0.1 --port 5111 '
                '--load-only en,ro,de,fr,es,ru,uk'
            ))
            return

        all_langs = [code for code, _ in settings.LANGUAGES if code != SOURCE_LANG]
        langs = options['langs'] or all_langs
        locale_root = settings.LOCALE_PATHS[0]

        for lang in langs:
            po_path = os.path.join(locale_root, lang, 'LC_MESSAGES', 'django.po')
            if not os.path.exists(po_path):
                self.stderr.write(f'  {lang}: no django.po (skipped)')
                continue
            self._translate_file(po_path, lang)

        if options['compile']:
            self.stdout.write('Compiling messages...')
            call_command('compilemessages')

        self.stdout.write(self.style.SUCCESS('Done.'))

    # --- LibreTranslate ---------------------------------------------------

    def _reachable(self):
        try:
            with urllib.request.urlopen(f'{self.lt_url}/languages', timeout=10) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _lt(self, texts, target):
        if not texts:
            return []
        payload = {'q': texts, 'source': SOURCE_LANG, 'target': target, 'format': 'text'}
        if self.lt_key:
            payload['api_key'] = self.lt_key
        req = urllib.request.Request(
            f'{self.lt_url}/translate',
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        out = data['translatedText']
        return out if isinstance(out, list) else [out]

    def _translate_strings(self, texts, target):
        """Placeholder-safe translation of a list of full strings."""
        structures = [_tokenize(t) for t in texts]

        cores = []
        refs = []  # (si, pi, lead, trail, core_index or None)
        for si, parts in enumerate(structures):
            for pi, (kind, val) in enumerate(parts):
                if kind != 'lit':
                    continue
                lead, core, trail = WS_RE.match(val).groups()
                if core:
                    refs.append((si, pi, lead, trail, len(cores)))
                    cores.append(core)
                else:
                    refs.append((si, pi, val, '', None))

        translated = []
        BATCH = 25
        for i in range(0, len(cores), BATCH):
            translated.extend(self._lt(cores[i:i + BATCH], target))

        repl = {}
        for (si, pi, lead, trail, ci) in refs:
            repl[(si, pi)] = lead if ci is None else f'{lead}{translated[ci]}{trail}'

        results = []
        for si, parts in enumerate(structures):
            out = []
            for pi, (kind, val) in enumerate(parts):
                out.append(val if kind == 'ph' else repl[(si, pi)])
            results.append(''.join(out))
        return results

    # --- .po handling -----------------------------------------------------

    def _needs(self, entry, lang):
        if entry.obsolete or entry.msgid == '':
            return False
        if lang in ADD_ONLY:
            if entry.msgid_plural:
                return not all((entry.msgstr_plural or {}).values())
            return not entry.msgstr
        if 'fuzzy' in entry.flags:
            return True
        if entry.msgid_plural:
            plurals = entry.msgstr_plural or {}
            if not all(plurals.values()):
                return True
            if _placeholders(entry.msgid) != _placeholders(plurals.get(0, '')):
                return True
            return any(_placeholders(entry.msgid_plural) != _placeholders(v)
                       for k, v in plurals.items() if k != 0)
        if not entry.msgstr:
            return True
        return _placeholders(entry.msgid) != _placeholders(entry.msgstr)

    def _translate_file(self, po_path, lang):
        po = polib.pofile(po_path)
        po.metadata['Language'] = lang

        pending = [e for e in po if self._needs(e, lang)]
        if not pending:
            self.stdout.write(f'  {lang}: nothing to translate (up to date).')
            return
        self.stdout.write(f'  {lang}: translating {len(pending)} entry/entries...')

        sources = []
        index = []  # (entry, kind) kind in {'s','p'}
        for e in pending:
            sources.append(e.msgid)
            index.append((e, 's'))
            if e.msgid_plural:
                sources.append(e.msgid_plural)
                index.append((e, 'p'))

        translated = self._translate_strings(sources, lang)

        nplurals = self._nplurals(po)
        for idx, (entry, kind) in enumerate(index):
            value = translated[idx]
            if entry.msgid_plural:
                if not entry.msgstr_plural:
                    entry.msgstr_plural = {n: '' for n in range(nplurals)}
                if kind == 's':
                    entry.msgstr_plural[0] = value
                else:
                    for n in range(1, nplurals):
                        entry.msgstr_plural[n] = value
            elif kind == 's':
                entry.msgstr = value
            if 'fuzzy' in entry.flags:
                entry.flags.remove('fuzzy')

        po.save(po_path)
        self.stdout.write(self.style.SUCCESS(f'  {lang}: wrote {len(pending)} translation(s).'))

    @staticmethod
    def _nplurals(po):
        header = po.metadata.get('Plural-Forms', 'nplurals=2;')
        m = re.search(r'nplurals\s*=\s*(\d+)', header)
        return int(m.group(1)) if m else 2
