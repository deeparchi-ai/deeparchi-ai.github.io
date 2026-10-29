"""AI Studio real-browser acceptance. Only explicit fake AI fixtures; no paid calls.
Run: .venv/bin/python tests/deepblm-studio-smoke.py
"""
import importlib.util
import os
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, expect

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('deep_ux', HERE / 'deepblm-deep-ux-smoke.py')
assert SPEC is not None and SPEC.loader is not None
ux = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ux)
OUT = os.environ.get('DEEPBLM_SCREENSHOT_DIR')


def shot(page, name):
    if OUT:
        folder = Path(OUT)
        folder.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(folder / (name + '.png')))


def visual_and_art(browser, base):
    for width, height in ((1440, 900), (1024, 600)):
        context, page, requests, errors, assets = ux.new_page(browser, base, width, height)
        try:
            names = set()
            ids = page.locator('#step-nav button').evaluate_all('(ns)=>ns.map(n=>n.dataset.step)')
            assert len(ids) == len(set(ids)) == 15
            assert page.locator('#step-nav h2').all_text_contents() == ['现状与差距', '战略选择', '战略执行', '领导力与价值观', '检查与修订']
            assert page.evaluate("Array.from(document.querySelectorAll('#step-nav .step-title')).every(n=>n.scrollWidth<=n.clientWidth+1)"), ('clipped navigation title', width)
            for index, step_id in enumerate(ids):
                page.locator(f'[data-step="{step_id}"]').click()
                expect(page.locator('#step-heading')).to_be_focused()
                art = page.locator('#step-content .studio-step-art')
                expect(art).to_have_js_property('naturalWidth', 1600)
                expect(art).to_have_js_property('naturalHeight', 1000)
                assert art.get_attribute('alt') == ''
                assert art.get_attribute('width') == '1600' and art.get_attribute('height') == '1000'
                names.add(Path(urlsplit(art.get_attribute('src')).path).name)
                intro = page.locator('.studio-step-intro').bounding_box()
                assert intro['height'] <= 160, (step_id, width, intro)
                footer = page.locator('.step-pager').bounding_box()
                assert footer['y'] + footer['height'] <= height + 1
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                if index in (0, 2, 6, 11, 13):
                    shot(page, f'studio-{step_id}-{width}')
            assert names == {'insight.webp', 'strategy.webp', 'execution.webp', 'foundation.webp', 'review.webp'}
            assert page.evaluate("Array.from(document.querySelectorAll('svg.studio-icon')).every(n=>n.getAttribute('aria-hidden')==='true' && n.getAttribute('focusable')==='false')")
            page.locator('[data-step="company-info"]').click()
            expect(page.locator('[data-step="company-info"] .studio-step-meter')).to_have_text('0/5')
            page.locator('[data-field="company-info-企业名称"] input.simple-input').fill('虚构视觉验收企业')
            expect(page.locator('[data-step="company-info"]')).to_have_attribute('data-completion', 'partial')
            expect(page.locator('[data-step="company-info"] .studio-step-meter')).to_have_text('1/5')
            assert not errors and not assets, (errors, assets)
            assert not any(urlsplit(u).netloc != urlsplit(base).netloc for u in requests)
        finally:
            context.close()
    print('PASS: actual five-group art on all 15 steps; readable nonclipped navigation, accurate counts, compact headers and fixed pager at 1440/1024x600')


def intents_and_pending(browser, base):
    context, page, requests, errors, assets = ux.new_page(browser, base)
    calls, reply = [], {'content': '虚构 AI 初稿：具体数据仍待核实。'}
    try:
        ux.configure(page)
        ux.install_fixture(page, calls, reply)
        field_id = 'company-info-主营业务'
        ux.open_target(page, field_id)
        expect(page.locator('[data-ai-intent]')).to_have_count(2)
        question = page.locator('#ai-question')
        original = '虚构人工要求：保留试点前提。'
        before_draft = page.evaluate('localStorage.getItem("deepblm-draft-v1")')
        question.fill(original)
        chip = page.locator('[data-ai-intent]').first
        chip.click()
        augmented = question.input_value()
        assert augmented.startswith(original + '\n') and len(augmented) > len(original)
        expect(question).to_be_focused()
        assert len(calls) == 0
        assert page.evaluate('localStorage.getItem("deepblm-draft-v1")') == before_draft
        expect(page.locator('#ai-intent-hint')).to_contain_text('仅下次主动生成')
        chip.click()
        assert question.input_value() == augmented
        expect(page.locator('#ai-intent-hint')).to_contain_text('不会重复添加')
        ux.generate(page, calls, reply, reply['content'])
        assert augmented in calls[0].post_data_json['messages'][-1]['content']
        expect(page.locator('.studio-ai-art')).not_to_be_visible()
        page.locator('[data-ai-view="edit"]').click()
        edited = '虚构人工编辑稿：保留可核验依据，不视为已验证。'
        page.locator('#ai-draft-editor').fill(edited)
        page.locator('[data-ai-intent]').last.click()
        expect(page.locator('.ai-result-card')).to_have_attribute('data-state', 'success')
        expect(page.locator('#ai-draft-editor')).to_have_value(edited)
        assert len(calls) == 1
        question.fill('x' * 8000)
        page.locator('[data-ai-intent]').last.click()
        expect(question).to_have_value('x' * 8000)
        expect(page.locator('#ai-intent-hint')).to_contain_text('原有文字未改动')
        page.locator('#ai-target-select').select_option('company-info-企业名称')
        expect(question).to_have_value('')
        expect(page.locator('[data-ai-intent]')).to_have_count(1)
        expect(page.locator('[data-ai-intent]')).to_have_attribute('data-ai-intent', 'identity')
        page.locator('#ai-target-select').select_option(field_id)
        expect(question).to_have_value('x' * 8000)
        expect(page.locator('#ai-draft-editor')).to_have_value(edited)
        question.fill('虚构上线前验收：保留已有依据。')
        page.locator('[data-ai-intent]').first.click()
        page.locator('[data-ai-view="compare"]').click()
        shot(page, 'studio-ai-compare-1440')
        page.evaluate("""() => {
          window.__studioPending = {count:0, aborted:false};
          window.fetch = (_url, options) => new Promise(resolve => {
            window.__studioPending.count++;
            options.signal.addEventListener('abort', () => {window.__studioPending.aborted=true;});
            window.__studioResolve = () => resolve(new Response(JSON.stringify({choices:[{message:{content:'虚构迟到结果，不得显示或采用'}}]}),{status:200}));
          });
        }""")
        page.locator('#ai-send').click()
        expect(page.locator('#ai-panel')).to_have_attribute('data-pending', 'true')
        for node in page.locator('[data-ai-intent]').all():
            expect(node).to_be_disabled()
        assert page.evaluate('window.__studioPending.count') == 1
        assert page.locator('.ai-result-card').evaluate("n=>getComputedStyle(n,'::after').animationName") == 'studio-spin'
        page.emulate_media(reduced_motion='reduce')
        assert page.locator('.ai-result-card').evaluate("n=>getComputedStyle(n,'::after').animationName") == 'none'
        page.locator('#ai-cancel').click()
        expect(page.locator('#ai-panel')).to_have_attribute('data-pending', 'false')
        assert page.evaluate('window.__studioPending.aborted')
        page.evaluate('async () => {window.__studioResolve(); await Promise.resolve(); await Promise.resolve();}')
        expect(page.locator('.ai-result-card')).to_have_attribute('data-state', 'empty')
        assert '虚构迟到结果' not in page.locator('#ai-result').inner_text()
        for node in page.locator('[data-ai-intent]').all():
            expect(node).to_be_enabled()
        assert page.locator('#ai-panel #ai-key, #ai-panel #ai-consent, #ai-panel #ai-disclosure').count() == 0
        assert len(calls) == 1 and not errors and not assets, (calls, errors, assets)
        assert page.evaluate('localStorage.getItem("deepblm-draft-v1")') == before_draft
    finally:
        context.close()
    print('PASS: chips append without sending/overwriting/duplication; limit atomicity, payload, cached edited draft, target isolation, pending/reduced-motion/cancel and late reply safety')


def fallbacks_and_mobile(browser, base):
    context = browser.new_context(viewport={'width': 1440, 'height': 900})
    page = context.new_page()
    _, errors, assets = ux.smoke.watch(page, base)
    page.route('**/deepblm-art/*.webp', lambda route: route.abort())
    try:
        page.goto(base + '/apps/deepblm.html?internal_test=1', wait_until='networkidle')
        expect(page.locator('#workspace')).to_be_visible()
        expect(page.locator('#step-content .studio-step-art')).to_be_hidden()
        field = page.locator('[data-field="company-info-企业名称"] input.simple-input')
        field.fill('虚构图片失败时的可用性验收')
        expect(field).to_have_value('虚构图片失败时的可用性验收')
        page.emulate_media(forced_colors='active', reduced_motion='reduce')
        expect(page.locator('.studio-step-visual')).to_be_hidden()
        ux.open_target(page, 'company-info-主营业务')
        expect(page.locator('.studio-ai-art')).to_be_hidden()
        expect(page.locator('#ai-question')).to_be_visible()
        assert not errors and not assets
    finally:
        context.close()
    for width in (320, 390, 820):
        context = browser.new_context(viewport={'width': width, 'height': 900}, is_mobile=True)
        page = context.new_page()
        urls, errors, assets = ux.smoke.watch(page, base)
        try:
            page.goto(base + '/apps/deepblm.html?internal_test=1', wait_until='networkidle')
            expect(page.locator('#companion')).to_be_visible()
            image = page.locator('.studio-companion-art img')
            image.scroll_into_view_if_needed()
            expect(image).to_have_js_property('naturalWidth', 1600)
            assert not any('deepblm-workspace.mjs' in u or 'deepblm-studio.mjs' in u or '/vendor/' in u for u in urls)
            assert page.locator('#ai-key').count() == 0
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            shot(page, f'studio-mobile-{width}')
            assert not errors and not assets
        finally:
            context.close()
    print('PASS: image-failure manual editing, forced-colors/reduced-motion fallback; lightweight 320/390/820 mobile with real local art and no editor or Key form')


if __name__ == '__main__':
    with ux.shared.site_url() as base, sync_playwright() as p:
        options = {'headless': True}
        if ux.shared.CHROME_PATH:
            options['executable_path'] = ux.shared.CHROME_PATH
        browser = p.chromium.launch(**options)
        try:
            visual_and_art(browser, base)
            intents_and_pending(browser, base)
            fallbacks_and_mobile(browser, base)
        finally:
            browser.close()
    print('PASS: DeepBLM AI Studio visual, interaction and accessibility acceptance')
