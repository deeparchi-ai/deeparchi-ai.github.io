"""Real Chromium acceptance for the English homepage; no mail or live analytics sent.

Run from the worktree using the source venv Python. BASE_URL/CHROME_PATH are optional,
as in visual-smoke.py. Screenshots and results stay inside this worktree.
"""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('homepage_smoke', ROOT / 'tests/visual-smoke.py')
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)
OUT = ROOT / 'test-results/english-homepage'
WIDTHS = (320, 390, 820, 1440)
HAN = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')
STAGES = ['Discover services', 'Describe requirements', 'Confirm scope and authorization',
          'View progress', 'Receive sample deliverable']
CONFIG = {'version': '1', 'enabled': True, 'endpoint': 'https://metrics.example.org/receive',
          'consent_required': True}


def log(path, status):
    with (ROOT / 'progress.md').open('a') as stream:
        stream.write(f'- {datetime.now(timezone.utc).isoformat(timespec="seconds")} | {path.resolve()} | {status}\n')


def screenshot(page, name):
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / (name + '.png')
    page.screenshot(path=str(target), full_page=True)
    log(target, 'Captured real Chromium screenshot; assertions passed to this point')


def clean_english(page):
    text = page.locator('body').inner_text()
    assert 'Legal company name: 上海申渡架固信息技术有限公司' in text
    text = text.replace('Legal company name: 上海申渡架固信息技术有限公司', '').replace('中文 (Chinese)', '')
    assert not HAN.search(text), text
    # Check accessible labels as well as rendered text. Hidden dialogs are checked when opened.
    attrs = page.locator('[aria-label]:visible, [alt]:visible, [title]:visible').evaluate_all(
        "els => els.flatMap(e => ['aria-label','alt','title'].map(a => e.getAttribute(a) || ''))")
    assert all(not HAN.search(value) for value in attrs), attrs


def no_overflow(page, dialog=None):
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    if dialog:
        assert page.locator(dialog).evaluate('e => e.scrollWidth <= e.clientWidth + 1')
    else:
        clipped = page.locator('.product .button:visible, .tool-card .button:visible').evaluate_all("""els => els.filter(e => {
          const r=e.getBoundingClientRect(), p=e.closest('article').getBoundingClientRect();
          return r.left < p.left-1 || r.right > p.right+1;
        }).map(e=>e.outerHTML)""")
        assert not clipped, clipped


def trap(page, selector):
    controls = page.locator(selector).locator(
        'a[href]:visible,button:visible,input:visible,select:visible,textarea:visible,[tabindex="0"]:visible')
    controls.first.focus()
    page.keyboard.press('Shift+Tab')
    assert controls.last.evaluate('e => e === document.activeElement')
    page.keyboard.press('Tab')
    assert controls.first.evaluate('e => e === document.activeElement')


def dismiss(page, selector, trigger):
    # Native focus restoration can precede the queued close handler, which also
    # restores focus. Wait for that handler before focusing the next control.
    shared.wait_closed(page, selector, lambda: page.keyboard.press('Escape'))
    expect(page.locator(selector)).not_to_be_visible()
    expect(page.locator(trigger)).to_be_focused()


def new_context(browser, base, width=1440, javascript=True):
    context = browser.new_context(viewport={'width': width, 'height': 960},
                                  java_script_enabled=javascript, reduced_motion='reduce', locale='en-US')
    outbound = []
    local = urlsplit(base).netloc

    def guard(route):
        request = route.request
        if request.method != 'GET' or urlsplit(request.url).netloc != local:
            outbound.append(f'{request.method} {request.url}')
            route.abort()
        else:
            route.continue_()
    context.route('**/*', guard)
    page = context.new_page()
    errors, responses, failures = shared.page_errors(page)
    return context, page, (outbound, errors, responses, failures)


def check_language(page, base, width, javascript):
    if javascript and width <= 600:
        page.locator('.menu-button').click()
        expect(page.locator('.menu-button')).to_have_attribute('aria-label', 'Close navigation menu')
        page.keyboard.press('Escape')
        expect(page.locator('.menu-button')).to_be_focused()
        expect(page.locator('.menu-button')).to_have_attribute('aria-label', 'Open navigation menu')
        page.locator('.menu-button').click()
    page.locator('a.language-switch').click()
    expect(page.locator('html')).to_have_attribute('lang', 'zh-CN')
    expect(page.locator('#hero-title')).to_have_text('让技术看得清，让成果走得通。')
    if javascript and width <= 600:
        expect(page.locator('.menu-button')).to_have_attribute('aria-label', '打开导航菜单')
        page.locator('.menu-button').click()
        expect(page.locator('.menu-button')).to_have_attribute('aria-label', '关闭导航菜单')
    page.locator('a.language-switch').click()
    expect(page.locator('html')).to_have_attribute('lang', 'en')
    assert urlsplit(page.url).path == '/en.html'
    assert page.locator('#hero-title').inner_text().startswith('See technology clearly.')


def check_static(browser, base, width):
    context, page, diagnostics = new_context(browser, base, width, javascript=False)
    try:
        page.goto(base + '/en.html', wait_until='networkidle')
        expect(page.locator('h1')).to_contain_text('See technology clearly.')
        assert not page.locator('[data-js]:visible').count()
        assert page.locator('#capabilities noscript').inner_text().startswith('Enable JavaScript')
        page.locator('#open-insight').click()
        expect(page.locator('#insight-details')).to_be_visible()
        page.locator('#insight-details > summary').click()
        assert page.locator('#insight-details').get_attribute('open') is not None
        for tier in ('p1', 'p2', 'p3'):
            expect(page.locator('#insight-' + tier + '-title')).to_be_visible()
        assert page.locator('#insight-content a[href="mailto:contact@deeparchi.com.cn"]').count() == 1
        for _ in range(2):
            page.locator('#open-transfer').press('Enter')
            expect(page.locator('#transfer-details-body')).to_be_visible()
            assert 'we do not guarantee' in page.locator('#transfer-details-body').inner_text()
            page.locator('#open-transfer').press('Space')
            expect(page.locator('#transfer-details-body')).not_to_be_visible()
        no_overflow(page)
        clean_english(page)
        screenshot(page, f'{width}-no-js')
        check_language(page, base, width, False)
        assert not any(diagnostics), diagnostics
    finally:
        context.close()


def check_live(browser, base, width):
    context, page, diagnostics = new_context(browser, base, width)
    try:
        page.goto(base + '/en.html?internal_test=1', wait_until='networkidle')
        expect(page.locator('#insight-details')).not_to_be_visible()
        clean_english(page)
        no_overflow(page)
        assert page.locator('.button.primary').first.evaluate('e => getComputedStyle(e).backgroundColor') == 'rgb(0, 102, 204)'
        screenshot(page, f'{width}-js')
        page.locator('#open-insight').click()
        expect(page.locator('#insight-dialog [data-close]')).to_be_focused()
        trap(page, '#insight-dialog')
        no_overflow(page, '#insight-dialog')
        clean_english(page)
        dismiss(page, '#insight-dialog', '#open-insight')
        page.locator('#open-insight').click()
        page.locator('#insight-consulting').click()
        expect(page.locator('dialog[open]')).to_have_count(1)
        expect(page.locator('#demand-source')).to_have_text('Source: Service inquiry')
        expect(page.locator('#demand-dialog [data-close]')).to_be_focused()
        trap(page, '#demand-dialog')
        dismiss(page, '#demand-dialog', '#open-insight')
        for _ in range(2):
            page.locator('#open-transfer').press('Enter')
            expect(page.locator('#transfer-details-body')).to_be_visible()
            page.locator('#open-transfer').press('Space')
            expect(page.locator('#transfer-details-body')).not_to_be_visible()
        page.locator('#open-a2a').click()
        expect(page.locator('#a2a-dialog [data-close]')).to_be_focused()
        trap(page, '#a2a-dialog')
        for index, title in enumerate(STAGES):
            expect(page.locator('#a2a-stage-title')).to_have_text(title)
            expect(page.locator('#a2a-stage-label')).to_have_text(f'SAMPLE {index + 1} / 5 · Deep BLM')
            expect(page.locator('.stages [aria-current="step"]')).to_have_text(title)
            assert page.locator('#a2a-stage-copy').inner_text()
            no_overflow(page, '#a2a-dialog')
            clean_english(page)
            if index < 4:
                expect(page.locator('#a2a-artifact')).not_to_be_visible()
                page.locator('#a2a-next').click()
        expect(page.locator('#a2a-intent')).to_be_focused()
        artifact = json.loads(page.locator('#a2a-artifact').inner_text())
        assert artifact['kind'] == 'sample-deliverable' and artifact['service_id'] == 'deep-blm'
        assert artifact['sample'] is True and artifact['task_executed'] is False
        assert artifact['findings'] is None and artifact['requires_human_review'] is True
        assert len(artifact['deliverable_structure']) == 3
        screenshot(page, f'{width}-a2a-stage-5')
        page.locator('#a2a-reset').click()
        expect(page.locator('#a2a-stage-title')).to_have_text(STAGES[0])
        expect(page.locator('#a2a-artifact')).not_to_be_visible()
        for _ in range(4):
            page.locator('#a2a-next').click()
        page.locator('#a2a-intent').click()
        expect(page.locator('#demand-source')).to_have_text('Source: A2A interest / Deep BLM')
        expect(page.locator('dialog[open]')).to_have_count(1)
        dismiss(page, '#demand-dialog', '#open-a2a')
        page.locator('#open-a2a').click()
        expect(page.locator('#a2a-stage-title')).to_have_text(STAGES[0])
        expect(page.locator('#a2a-artifact')).not_to_be_visible()
        page.locator('#a2a-next').click()
        page.locator('#a2a-product').select_option('deep-blm')
        expect(page.locator('#a2a-stage-title')).to_have_text(STAGES[0])
        dismiss(page, '#a2a-dialog', '#open-a2a')
        for selector, category in [('#insight-card-consulting', 'Service inquiry'),
                ('#transfer-card-consulting', 'Service inquiry'), ('#contact-consulting', 'Service inquiry'),
                ('#contact-partnership', 'Partnership'), ('#contact-a2a', 'A2A interest'),
                ('#contact [data-intent="integration"]', 'Tool integration')]:
            page.locator(selector).click()
            expect(page.locator('#demand-source')).to_have_text('Source: ' + category)
            clean_english(page)
            dismiss(page, '#demand-dialog', selector)
        check_draft(page, width)
        check_language(page, base, width, True)
        assert not any(diagnostics), diagnostics
    finally:
        context.close()


def check_draft(page, width):
    trigger = '#contact [data-intent="general"]'
    page.locator(trigger).click()
    submit = page.locator('#demand-form button[type="submit"]')
    submit.click()
    expect(page.locator('#draft')).not_to_be_visible()
    assert page.locator('#problem').evaluate('e => e.validationMessage') == 'Please briefly describe your business problem.'
    page.locator('#problem').fill('   ')
    submit.click()
    assert page.locator('#problem').evaluate('e => e.validationMessage') == 'Please briefly describe your business problem.'
    text = '<img src=x onerror="window.BAD=true"> + 50% & project\nSecond line'
    page.locator('#problem').fill(text)
    submit.click()
    expect(page.locator('#draft')).to_be_visible()
    assert 'nothing has been sent' in page.locator('#draft').inner_text()
    values = parse_qs(urlsplit(page.locator('#draft-mailto').get_attribute('href')).query)
    assert text in values['body'][0]
    assert values['subject'] == ['DeepArchi | General inquiry']
    assert 'Not provided' in values['body'][0]
    assert page.locator('#draft-text img').count() == 0 and page.evaluate('window.BAD === undefined')
    assert 'project' not in page.url
    page.evaluate("Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async text=>{window.copied=text;}}})")
    page.locator('#copy-draft').click()
    expect(page.locator('#copy-status')).to_have_text('Copied.')
    assert page.evaluate('window.copied') == page.locator('#draft-text').inner_text()
    page.evaluate("Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async()=>{throw new Error('fixture denial')}}})")
    page.locator('#copy-draft').click()
    expect(page.locator('#copy-status')).to_contain_text('copy it manually')
    # Prevent OS mail-client launch while exercising the real click handler.
    page.locator('#draft-mailto').evaluate("e => e.addEventListener('click',ev=>ev.preventDefault(),{once:true})")
    page.locator('#draft-mailto').click()
    page.locator('#result').fill('Edited outcome')
    expect(page.locator('#draft')).not_to_be_visible()
    assert page.locator('#draft-mailto').get_attribute('href') is None
    for selector, length in [('#problem', 500), ('#result', 500), ('#constraints', 300)]:
        page.locator(selector).fill('&' * length)
    submit.click()
    expect(page.locator('#copy-status')).to_contain_text('This draft is long')
    assert 'body' not in parse_qs(urlsplit(page.locator('#draft-mailto').get_attribute('href')).query)
    assert '&' * 500 in page.locator('#draft-text').inner_text()
    trap(page, '#demand-dialog')
    no_overflow(page, '#demand-dialog')
    clean_english(page)
    screenshot(page, f'{width}-draft')
    # Programmatic over-limit input exercises the local draft error branch; it is not typed UI input.
    page.locator('#problem').evaluate("e => e.value = 'x'.repeat(501)")
    page.locator('#demand-form').evaluate('e => e.requestSubmit()')
    assert page.locator('#problem').evaluate('e => e.validationMessage') == 'Please check the text lengths and prepare the draft again.'
    dismiss(page, '#demand-dialog', trigger)
    expect(page.locator('#problem')).to_have_value('')
    expect(page.locator('#draft')).not_to_be_visible()
    page.locator('#copy-email').click()
    expect(page.locator('#email-status')).to_have_text('Automatic copying is unavailable. Copy manually: contact@deeparchi.com.cn')


def check_analytics(browser, base):
    context, page, diagnostics = new_context(browser, base)
    context.route('**/analytics-config.json', lambda route: route.fulfill(json=CONFIG))
    try:
        page.goto(base + '/en.html?internal_test=1', wait_until='networkidle')
        banner = page.locator('[data-analytics-banner]')
        expect(banner).to_be_visible()
        # Configuration fetch/render is asynchronous; wait for the required state.
        expect(page.locator('[data-analytics-status]').first).to_contain_text('no live reporting')
        banner.locator('[data-consent="reject"]').click()
        expect(banner).not_to_be_visible()
        expect(page.locator('[data-analytics-feedback]')).to_contain_text('has not been given')
        panel = page.locator('footer [data-analytics]')
        panel.locator('summary').click()
        panel.locator('[data-consent="accept"]').click()
        expect(panel).to_contain_text('Anonymous analytics is allowed')
        clean_english(page)
        # Actual English UI handlers with only an explicit in-memory analytics transport.
        page.evaluate("""async()=>{
          window.fixtureEvents=[];
          const {initAnalytics}=await import(document.querySelector('script[type="module"]').src);
          await initAnalytics({transport:async(endpoint,payload)=>{window.fixtureEvents.push(payload);return {ok:true};}});
        }""")
        panel.locator('[data-consent="accept"]').click()
        page.locator('#transfer-card-consulting').click()
        page.locator('#problem').fill('PRIVATE draft content')
        page.locator('#demand-form button[type="submit"]').click()
        page.locator('#draft-mailto').evaluate("e=>e.addEventListener('click',ev=>ev.preventDefault(),{once:true})")
        page.locator('#draft-mailto').click()
        dismiss(page, '#demand-dialog', '#transfer-card-consulting')
        page.locator('#open-a2a').click()
        page.locator('#a2a-product').select_option('deep-blm')
        for _ in range(4):
            page.locator('#a2a-next').click()
        page.locator('#a2a-intent').click()
        dismiss(page, '#demand-dialog', '#open-a2a')
        page.wait_for_function("window.fixtureEvents.some(e=>e.event==='a2a_interest')", timeout=20000)
        events = page.evaluate('window.fixtureEvents')
        assert {e['step'] for e in events if e['event'] == 'a2a_step'} == {1, 2, 3, 4, 5}
        assert {'mail_draft_ready', 'mailto_click', 'intent_open', 'a2a_interest'} <= {e['event'] for e in events}
        allowed = {'version','event','service','category','surface','audience','is_test','session_id','event_id','step','source_origin','source_state'}
        assert all(set(e) <= allowed and e['is_test'] and e['audience'] == 'browser_interaction' for e in events)
        assert all(e['service'] is None for e in events if e['category'] == 'consulting')
        assert all(e['service'] in (None, 'deep-blm') for e in events)
        assert 'PRIVATE' not in json.dumps(events) and 'demo_complete' not in {e['event'] for e in events}
        panel.locator('[data-consent="reject"]').click()
        count = len(events)
        page.locator('#contact-partnership').click()
        dismiss(page, '#demand-dialog', '#contact-partnership')
        assert len(page.evaluate('window.fixtureEvents')) == count
        expect(panel).to_contain_text('has not been given')
        assert not any(diagnostics), diagnostics
    finally:
        context.close()
    for flag in ('doNotTrack', 'globalPrivacyControl'):
        context, page, diagnostics = new_context(browser, base)
        try:
            value = "'1'" if flag == 'doNotTrack' else 'true'
            context.add_init_script(f"Object.defineProperty(navigator,'{flag}',{{get:()=>{value}}})")
            context.route('**/analytics-config.json', lambda route: route.fulfill(json=CONFIG))
            page.goto(base + '/en.html?internal_test=1', wait_until='networkidle')
            page.locator('footer summary').click()
            expect(page.locator('footer [data-analytics-status]')).to_contain_text('DNT/GPC is respected')
            expect(page.locator('[data-analytics-banner]')).not_to_be_visible()
            assert not page.locator('[data-consent]:visible').count()
            clean_english(page)
            assert not any(diagnostics), diagnostics
        finally:
            context.close()


def check_legacy_demo(browser, base):
    # The public Deep BLM CTA navigates to its Chinese tool. This explicitly injected
    # fixture exercises the retained demo dialog's real initializer and focus handlers.
    context, page, diagnostics = new_context(browser, base)
    fixture = (ROOT / 'en.html').read_text().replace('</main>',
        '<button id="fixture-demo" data-demo="deep-blm">Fixture demo trigger</button></main>')
    context.route('**/en.html?legacy_fixture=1', lambda route: route.fulfill(body=fixture, content_type='text/html'))
    try:
        page.goto(base + '/en.html?legacy_fixture=1', wait_until='networkidle')
        page.locator('#fixture-demo').click()
        expect(page.locator('#demo-title')).to_have_text('Deep BLM')
        expect(page.locator('#demo-problem')).to_contain_text('A fictional team')
        expect(page.locator('#demo-output li')).to_have_count(3)
        trap(page, '#demo-dialog')
        clean_english(page)
        dismiss(page, '#demo-dialog', '#fixture-demo')
        page.locator('#fixture-demo').click()
        page.locator('#demo-intent').click()
        expect(page.locator('#demand-source')).to_have_text('Source: Product inquiry / Deep BLM')
        expect(page.locator('dialog[open]')).to_have_count(1)
        dismiss(page, '#demand-dialog', '#fixture-demo')
        assert not any(diagnostics), diagnostics
    finally:
        context.close()


def main():
    with shared.site_url() as base:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=shared.CHROME_PATH, headless=True)
            try:
                for width in WIDTHS:
                    check_static(browser, base, width)
                    check_live(browser, base, width)
                check_analytics(browser, base)
                check_legacy_demo(browser, base)
            finally:
                browser.close()
    OUT.mkdir(parents=True, exist_ok=True)
    result = OUT / 'result.json'
    result.write_text(json.dumps({'status': 'passed', 'widths': WIDTHS, 'javascript': [False, True],
                                  'time': datetime.now(timezone.utc).isoformat()}, indent=2) + '\n')
    log(result, 'PASS: real Chromium English homepage acceptance')
    print('PASS: English homepage, language links, four widths, no-JS, dialogs/focus/Escape, five A2A stages, drafts and analytics guards')


if __name__ == '__main__':
    main()
