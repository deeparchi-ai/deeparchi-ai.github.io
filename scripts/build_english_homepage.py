#!/usr/bin/env python3
"""Build the static English homepage from the Chinese page and local dictionary.

Run --check to verify generated content and shared module cache versions offline.
No network access or runtime translation service is used.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'export const EN = '

def english_page():
    data = (ROOT / 'assets/homepage-locale.mjs').read_text()
    strings = json.loads(data[len(PREFIX):data.index(';\n\n')])
    page = (ROOT / 'index.html').read_text()
    for source, target in sorted(strings.items(), key=lambda item: -len(item[0])):
        page = page.replace(source, escape(target, quote=True))
    page = page.replace('lang="zh-CN"', 'lang="en"', 1)
    page = page.replace('href="en.html" lang="en" hreflang="en" aria-label="English homepage">English',
                        'href="index.html" lang="zh-CN" hreflang="zh-CN" aria-label="Chinese homepage">中文 (Chinese)')
    return page

def log(path, status):
    with (ROOT / 'progress.md').open('a') as stream:
        stream.write(f'- {datetime.now(timezone.utc).isoformat(timespec="seconds")} | {path.resolve()} | {status}\n')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    expected = english_page()
    target = ROOT / 'en.html'
    if args.check:
        assert target.read_text() == expected, 'en.html is stale; run scripts/build_english_homepage.py'
        for page in ('index.html', 'en.html', 'developers.html', 'privacy.html'):
            asset = 'assets/site.mjs'
            version = sha256((ROOT / asset).read_bytes()).hexdigest()[:12]
            assert f'{asset}?v={version}' in (ROOT / page).read_text(), page
        locale_version = sha256((ROOT / 'assets/homepage-locale.mjs').read_bytes()).hexdigest()[:12]
        assert f"./homepage-locale.mjs?v={locale_version}" in (ROOT / 'assets/site.mjs').read_text()
        print('PASS: generated English homepage and shared module cache versions')
    else:
        target.write_text(expected)
        log(target, 'Generated static English homepage; validation pending')

if __name__ == '__main__':
    main()
