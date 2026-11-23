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
P3_INTRO = '        <p>For specific technology choices, product plans, competitive strategies or business development needs, we conduct focused research and solution design, with action preparation, implementation coordination and review support within the agreed scope.</p>\n'
P3_DELIVERABLES = '        <div class="insight-deliverables">\n'
LI1_SERVICES = '''        <!-- english-only:start:li1-services -->
        <p><strong>systems assessment</strong>: Clarify your business context, application scenarios and constraints to identify the key questions, feasibility considerations and risks for an agreed assessment.</p>
        <p><strong>technology selection</strong>: Compare technology options using research evidence and expert analysis to develop judgments and recommendations in your business context.</p>
        <p><strong>migration planning</strong>: Define a staged plan with agreed scope, milestones and validation goals, reviewing risks and decision criteria before the next stage.</p>
        <!-- english-only:end:li1-services -->
'''

def insert_li1_services(page):
    anchor = P3_INTRO + P3_DELIVERABLES
    if page.count(anchor) != 1:
        raise ValueError('Expected exactly one LI-1 services anchor')
    if 'english-only:' in page:
        raise ValueError('Unexpected English-only marker in generated source')
    return page.replace(anchor, P3_INTRO + LI1_SERVICES + P3_DELIVERABLES, 1)

def english_page():
    data = (ROOT / 'assets/homepage-locale.mjs').read_text()
    strings = json.loads(data[len(PREFIX):data.index(';\n\n')])
    page = (ROOT / 'index.html').read_text()
    for source, target in sorted(strings.items(), key=lambda item: -len(item[0])):
        page = page.replace(source, escape(target, quote=True))
    page = page.replace('lang="zh-CN"', 'lang="en"', 1)
    page = page.replace('href="en.html" lang="en" hreflang="en" aria-label="English homepage">English',
                        'href="index.html" lang="zh-CN" hreflang="zh-CN" aria-label="Chinese homepage">中文 (Chinese)')
    return insert_li1_services(page)

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
