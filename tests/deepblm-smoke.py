"""Real browser acceptance. AI routes below are explicit, non-real fixtures; never paid calls.
Run: .venv/bin/python tests/deepblm-smoke.py (optional BASE_URL / CHROME_PATH /
DEEPBLM_SCREENSHOT_DIR). Reuses the existing local HTTP server helper.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
from html.parser import HTMLParser
import importlib.util
import json
import os

spec = importlib.util.spec_from_file_location("site_smoke", Path(__file__).with_name("visual-smoke.py"))
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)
from playwright.sync_api import sync_playwright, expect

DRAFT = "deepblm-draft-v1"
REMEMBERED = "deepblm-remembered-key-v1"
PREFERENCES = "deepblm-preferences-v1"
KEY_FIXTURE = "fixture-only-not-a-real-api-key-DO-NOT-USE"
ENDPOINT_FIXTURE = "https://api.fixture-provider.example.org/v1/chat/completions"
XSS = '''虚构验收 **内容** </textarea><img src="https://leak.fixture-provider.example.org/pixel" onerror="window.__deepblmXSS=1"><svg onload="window.__deepblmXSS=2"></svg><iframe src="https://leak.fixture-provider.example.org"></iframe><style>@import 'https://leak.fixture-provider.example.org/style';</style><script>window.__deepblmXSS=3</script>\n[危险链接](javascript:alert(1)) [安全链接](https://www.deeparchi.com.cn/)'''


class SafeHTML(HTMLParser):
    def handle_starttag(self, tag, attrs):
        assert tag not in {"script", "img", "svg", "math", "iframe", "object", "embed", "form", "input", "video", "audio", "style", "link"}, tag
        for name, value in attrs:
            assert not name.startswith("on") and name != "style", (tag, name)
            if name == "href":
                assert value.startswith(("https://", "http://", "mailto:")), value


def field(page, field_id):
    return page.locator(f'[data-field="{field_id}"]')


def write_editor(page, field_id, value):
    # Uses the real EasyMDE/CodeMirror instance, not an emulated editor.
    box = field(page, field_id)
    if box.locator('.CodeMirror').count():
        box.locator('.CodeMirror').evaluate('(node, value) => node.CodeMirror.setValue(value)', value)
    else:
        box.locator('.simple-input').fill(value)


def field_value(page, field_id):
    box = field(page, field_id)
    if box.locator('.CodeMirror').count():
        return box.locator('.CodeMirror').evaluate('node => node.CodeMirror.getValue()')
    return box.locator('.simple-input').input_value()


def activate(page, selector):
    target = page.locator(selector) if isinstance(selector, str) else selector
    # Open the real disclosure before clicking its action, including nested field menus.
    menu = target.locator('xpath=ancestor::details[contains(@class,"disclosure-menu")]')
    if menu.count() and menu.get_attribute('open') is None:
        menu.locator(':scope > summary').click()
    target.click()


def preview(page, field_id):
    box = field(page, field_id)
    toggle = box.locator('.preview-toggle')
    if toggle.get_attribute('aria-expanded') == 'false':
        toggle.click()
    expect(box.locator('.preview-pane')).to_be_visible()


def current_draft(page):
    return page.evaluate('(key) => localStorage.getItem(key)', DRAFT)


def exported(page, selector, directory):
    with page.expect_download() as event:
        activate(page, selector)
    download = event.value
    target = Path(directory) / download.suggested_filename
    download.save_as(target)
    return target


def chooser_import(page, path):
    with page.expect_file_chooser() as event:
        activate(page, '#import-json')
    event.value.set_files(str(path))
    expect(page.locator('#import-file')).to_have_value('', timeout=5000)


def no_overflow(page):
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')


def safe_preview(page):
    assert page.evaluate('window.__deepblmXSS === undefined')
    assert page.locator('.rich-content script, .rich-content img, .rich-content svg, .rich-content iframe, .rich-content [onerror], .rich-content [onload]').count() == 0
    assert page.locator('.rich-content a[href^="javascript:"], .rich-content a[href^="data:"], .rich-content a[href^="//"]').count() == 0
    for anchor in page.locator('.rich-content a[href]').all():
        assert anchor.get_attribute('rel') == 'noopener noreferrer'


def watch(page, base):
    requests, errors, failed_assets = [], [], []
    origin = urlsplit(base).netloc
    page.on('request', lambda request: requests.append(request.url))
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('response', lambda response: failed_assets.append(response.url) if response.status >= 400 and urlsplit(response.url).netloc == origin else None)
    # No request to any third party can leave the test browser. The AI fixture is installed explicitly later.
    page.route('**/*', lambda route: route.continue_() if urlsplit(route.request.url).netloc == origin else route.abort())
    return requests, errors, failed_assets


def check_mobile(browser, base):
    for width in (320, 390, 820):
        page = browser.new_page(viewport={'width': width, 'height': 900})
        requests, errors, assets = watch(page, base)
        page.goto(base + '/apps/deepblm.html?internal_test=1', wait_until='networkidle')
        expect(page.locator('#companion')).to_be_visible()
        for text in ['15 个步骤', '没有账号', '本机浏览器', '在电脑上', '战略研讨']:
            assert text in page.locator('main').inner_text()
        expect(page.get_by_role('link', name='咨询规划需求')).to_be_visible()
        expect(page.get_by_role('link', name='返回官网服务')).to_be_visible()
        assert page.locator('#ai-key, .CodeMirror, #ai-panel').count() == 0
        assert not any('/vendor/' in u or 'deepblm-workspace' in u or 'deepblm-data' in u or 'deepblm-ui' in u or 'deepblm-security' in u or 'deepblm-credentials' in u or 'signals.mjs' in u or 'analytics-config' in u for u in requests), requests
        assert all(urlsplit(u).netloc == urlsplit(base).netloc for u in requests), requests
        assert page.locator('.brand-logo').evaluate('e => e.complete && e.naturalWidth === 498 && getComputedStyle(e).height === "88px"')
        no_overflow(page)
        assert '上海申渡架固' in page.locator('footer').inner_text()
        screenshot(page, f'companion-{width}.png')
        assert not errors and not assets, (errors, assets)
        page.close()
    # Entry discovery survives disabled JavaScript on both phone and desktop.
    for width in (390, 1440):
        context = browser.new_context(java_script_enabled=False, viewport={'width': width, 'height': 900})
        page = context.new_page()
        page.goto(base + '/?internal_test=1')
        entry = page.locator('a[data-tool-entry="deep-blm"]')
        expect(entry).to_be_visible()
        assert entry.get_attribute('href') == 'apps/deepblm.html'
        entry.click()
        expect(page.locator('#companion')).to_be_visible()
        assert '完整编辑工作台需要 JavaScript' in page.locator('noscript').inner_text()
        context.close()


def screenshot(page, name):
    path = os.environ.get('DEEPBLM_SCREENSHOT_DIR')
    if path:
        Path(path).mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(Path(path) / name), full_page=True)


def check_desktop(browser, base, directory):
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    requests, errors, assets = watch(page, base)
    page.goto(base + '/?internal_test=1', wait_until='networkidle')
    expect(page.locator('a[data-tool-entry="deep-blm"]')).to_be_visible()
    requests.clear()  # Isolate workspace requests from the homepage modules loaded above.
    page.locator('a[data-tool-entry="deep-blm"]').click()
    expect(page.locator('#workspace')).to_be_visible()
    assert page.locator('#step-nav button').count() == 15
    assert page.locator('.CodeMirror').count() == 1
    assert page.locator('.simple-input').count() == 4
    assert page.locator('.simple-input').first.evaluate('e => e.tagName') == 'INPUT'
    assert page.locator('.simple-input').first.get_attribute('maxlength') == '40'
    assert page.locator('.nav-group').count() == 5
    assert [g.locator('h2').inner_text() for g in page.locator('.nav-group').all()] == ['现状与差距', '战略选择', '战略执行', '领导力与价值观', '检查与修订']
    assert [g.locator('button').count() for g in page.locator('.nav-group').all()] == [2, 4, 5, 2, 2]
    expect(page.locator('.nav-foundation .nav-group-note')).to_have_text('贯穿战略与执行')
    assert page.locator('.nav-group').nth(1).locator('button').first.locator('.step-title').inner_text() == '3. 市场洞察'
    assert [b.inner_text() for b in page.locator('.nav-foundation .step-title').all()] == ['12. 领导力', '13. 价值观']
    # Sidebar exposes real per-step completion, counted from nonblank field values only.
    expect(page.locator('[data-step="company-info"] .step-completion')).to_have_text('未开始 · 0/5')
    expect(page.locator('[data-step="gap"] .step-completion')).to_have_text('未开始 · 0/2')
    expect(page.locator('#planning-name')).to_have_text('未命名规划')
    expect(page.locator('#next-step')).to_have_text('下一步：差距分析')
    expect(page.locator('.preview-pane')).not_to_be_visible()
    narrative = field(page, 'company-info-企业现状').locator('.CodeMirror').bounding_box()
    assert 100 <= narrative['height'] <= 180  # EasyMDE maxHeight must not force a 430px minimum.
    last_field = field(page, 'company-info-企业现状').bounding_box()
    assert last_field['y'] + last_field['height'] <= page.locator('.step-pager').bounding_box()['y']
    assert page.locator('.site-header').is_hidden() and page.locator('.deepblm-page-title').is_hidden()
    assert page.locator('body > footer').is_hidden()
    assert abs(page.locator('.workspace-topbar').bounding_box()['height'] - 60) <= 1
    assert 230 <= page.locator('.step-sidebar').bounding_box()['width'] <= 260
    assert 260 <= page.locator('.context-sidebar').bounding_box()['width'] <= 290
    assert current_draft(page) is None
    page.locator('#writing-example summary').click()
    expect(page.locator('#writing-example')).to_contain_text('示例（虚构')
    assert current_draft(page) is None  # Read-only examples never enter the draft.
    page.locator('#writing-example summary').click()
    screenshot(page, 'workspace-empty-1440.png')
    # Native disclosure: arrow navigation, Escape, outside click and Tab dismissal.
    summary = page.locator('#export-menu > summary')
    summary.focus(); page.keyboard.press('ArrowDown')
    expect(page.locator('#export-json')).to_be_focused()
    page.keyboard.press('End'); expect(page.locator('#export-word')).to_be_focused()
    page.keyboard.press('Home'); expect(page.locator('#export-json')).to_be_focused()
    page.keyboard.press('Escape'); expect(summary).to_be_focused()
    assert page.locator('#export-menu').get_attribute('open') is None
    summary.click(); page.locator('#step-heading').click()
    assert page.locator('#export-menu').get_attribute('open') is None
    summary.focus(); page.keyboard.press('Enter'); page.keyboard.press('Tab')
    expect(page.locator('#export-json')).to_be_focused()
    page.keyboard.press('Tab'); page.keyboard.press('Tab'); page.keyboard.press('Tab')
    assert page.locator('#export-menu').get_attribute('open') is None
    assert page.locator('.workspace-brand img').evaluate('e => e.complete && getComputedStyle(e).objectFit === "contain"')
    assert page.locator('link[rel="icon"]').get_attribute('href') == '../assets/deeparchi-favicon.png'
    assert not any('signals.mjs' in u or 'analytics-config' in u for u in requests)
    # First edit uses the actual single-line native input.
    company = field(page, 'company-info-企业名称').locator('input.simple-input')
    company.click()
    page.keyboard.insert_text('虚构验收企业')
    page.wait_for_function('(k) => localStorage.getItem(k)?.includes("虚构验收企业")', arg=DRAFT)
    write_editor(page, 'company-info-企业名称', '甲' * 40)
    before_limit = current_draft(page)
    company.evaluate("e => {e.value = '乙'.repeat(41); e.dispatchEvent(new Event('input', {bubbles:true}));}")
    assert company.input_value() == '甲' * 40
    assert current_draft(page) == before_limit
    business = field(page, 'company-info-主营业务').locator('.simple-input')
    business.evaluate("e => {e.value = '甲'.repeat(100001); e.dispatchEvent(new Event('input', {bubbles:true}));}")
    assert business.input_value() == '' and current_draft(page) == before_limit
    write_editor(page, 'company-info-企业名称', '虚构验收企业')
    write_editor(page, 'company-info-主营业务', '虚构主营业务')
    expect(page.locator('#planning-name')).to_have_text('虚构验收企业')
    write_editor(page, 'company-info-企业现状', XSS)
    preview(page, 'company-info-企业现状')
    expect(field(page, 'company-info-企业现状').locator('.rich-content strong')).to_have_text('内容')
    safe_preview(page)
    before_narrative_limit = current_draft(page)
    write_editor(page, 'company-info-企业现状', '甲' * 100001)
    assert field_value(page, 'company-info-企业现状') == XSS
    assert current_draft(page) == before_narrative_limit
    # Field text/Markdown file chooser is real and respects the same validation path.
    text_path = Path(directory) / 'field-fixture.md'
    text_path.write_text('虚构行业导入', encoding='utf-8')
    with page.expect_file_chooser() as event:
        activate(page, field(page, 'company-info-行业描述').get_by_role('button', name='导入文本', include_hidden=True))
    event.value.set_files(str(text_path))
    expect(field(page, 'company-info-行业描述').locator('.simple-input')).to_have_value('虚构行业导入')
    page.locator('#save-later').click()
    expect(page.locator('#tool-message')).to_contain_text('可随时继续')
    saved = current_draft(page)
    page.reload(wait_until='networkidle')
    expect(page.locator('#workspace')).to_be_visible()
    assert field_value(page, 'company-info-企业名称') == '虚构验收企业'
    assert current_draft(page) == saved
    page.once('dialog', lambda dialog: dialog.accept())
    activate(page, '#reset-step')
    assert field_value(page, 'company-info-企业名称') == ''
    expect(page.locator('#planning-name')).to_have_text('未命名规划')
    activate(page, '#undo')
    assert field_value(page, 'company-info-企业名称') == '虚构验收企业'
    # Every real step renders, including both report and revision editing.
    field(page, 'company-info-企业名称').locator('input.simple-input').focus()
    for nav in page.locator('#step-nav button').all():
        nav.click()
        assert nav.get_attribute('aria-current') == 'step'
        expect(page.locator('#step-heading')).to_be_visible()
        if nav.get_attribute('data-step') == 'company-info':
            expect(field(page, 'company-info-企业名称').locator('input.simple-input')).to_be_focused()
        else:
            expect(page.locator('#step-heading')).to_be_focused()
        no_overflow(page)
    page.locator('[data-step="gap"]').click()
    table = field(page, 'gap-业绩差距')
    table.locator('textarea[data-row="0"][data-column="0"]').fill('虚构指标类别')
    table.locator('textarea[data-row="0"][data-column="1"]').fill(XSS)
    table_saved = current_draft(page)
    cell = table.locator('textarea[data-row="0"][data-column="0"]')
    cell.evaluate("e => {e.value = '甲'.repeat(8001); e.dispatchEvent(new Event('input', {bubbles:true}));}")
    assert cell.input_value() == '虚构指标类别'
    assert current_draft(page) == table_saved
    table.locator('[data-add-row]').click()
    assert field(page, 'gap-业绩差距').locator('tbody tr').count() == 2
    field(page, 'gap-业绩差距').locator('textarea[data-row="1"][data-column="4"]').fill('虚构第二行差距')
    activate(page, '#undo')
    assert field(page, 'gap-业绩差距').locator('textarea[data-row="1"][data-column="4"]').input_value() == ''
    activate(page, '#redo')
    assert field(page, 'gap-业绩差距').locator('textarea[data-row="1"][data-column="4"]').input_value() == '虚构第二行差距'
    field(page, 'gap-业绩差距').get_by_role('button', name='删除业绩差距第2行').click()
    assert field(page, 'gap-业绩差距').locator('tbody tr').count() == 1
    activate(page, '#undo')
    assert field(page, 'gap-业绩差距').locator('tbody tr').count() == 2
    page.locator('[data-step="strategy-validation"]').click()
    activate(page, '#basic-validation')
    assert '本地完整性检查' in field_value(page, 'strategy-validation-逻辑校验报告')
    expect(page.locator('.validation-disclaimer')).to_contain_text('不能证明战略逻辑正确')
    # Jump to an exact field, edit the real input, return to the same review position.
    row = page.locator('[data-missing-field="company-info-企业规模"]')
    row.scroll_into_view_if_needed()
    report_scroll = page.locator('#step-content').evaluate('e => e.scrollTop')
    row.get_by_role('button', name='去补充').click()
    target = field(page, 'company-info-企业规模').locator('.simple-input')
    expect(target).to_be_focused()
    box = target.bounding_box(); footer = page.locator('.step-pager').bounding_box()
    assert box['y'] >= 60 and box['y'] + box['height'] <= footer['y']
    target.fill('虚构规模待核实')
    page.locator('#return-report').click()
    row = page.locator('[data-missing-field="company-info-企业规模"]')
    expect(row).to_have_attribute('data-resolved', 'true')
    expect(row).to_contain_text('已补充')
    expect(row.get_by_role('button', name='查看')).to_be_focused()
    assert abs(page.locator('#step-content').evaluate('e => e.scrollTop') - report_scroll) <= 2
    # The editable report is preserved, even when current completeness changes.
    assert '本地完整性检查' in field_value(page, 'strategy-validation-逻辑校验报告')
    narrative = page.locator('[data-missing-field="gap-机会差距"]')
    narrative.get_by_role('button', name='去补充').click()
    expect(field(page, 'gap-机会差距').locator('.CodeMirror textarea')).to_be_focused()
    write_editor(page, 'gap-机会差距', '虚构机会说明')
    page.locator('#return-report').click()
    expect(page.locator('[data-missing-field="gap-机会差距"]')).to_have_attribute('data-resolved', 'true')
    write_editor(page, 'strategy-validation-逻辑校验报告', XSS + '\n## 虚构修订建议\n- 补充市场依据')
    page.locator('[data-step="revision"]').click()
    activate(page, '#revision-from-report')
    assert '虚构修订建议' in field_value(page, 'revision-修改建议列表')
    preview(page, 'revision-修改建议列表')
    safe_preview(page)
    page.locator('[data-missing-field="values-核心价值观"]').get_by_role('button', name='去补充').click()
    write_editor(page, 'values-核心价值观', '虚构价值观，待团队确认')
    page.locator('#return-report-footer').click()
    expect(page.locator('#step-heading')).to_have_text('根据校验建议修改')
    expect(page.locator('[data-missing-field="values-核心价值观"]')).to_have_attribute('data-resolved', 'true')
    # Explicit non-real fixture AI; no provider is contacted.
    page.locator('[data-step="strategy-validation"]').click()
    activate(page, field(page, 'strategy-validation-逻辑校验报告').locator('[data-ai-field]'))
    expect(page.locator('#ai-panel')).to_be_visible()
    bounds = page.locator('#ai-panel').bounding_box()
    assert 0 <= bounds['y'] and bounds['y'] + bounds['height'] <= 1000
    assert page.locator('#ai-panel').get_attribute('aria-labelledby') == 'ai-heading'
    expect(page.locator('#ai-panel #ai-disclosure, #ai-panel #ai-destination, #ai-panel #ai-consent')).to_have_count(0)
    # Escape closes and restores focus to the direct field AI action.
    page.keyboard.press('Escape'); expect(page.locator('#ai-panel')).not_to_be_visible()
    expect(field(page, 'strategy-validation-逻辑校验报告').locator('[data-ai-field]')).to_be_focused()
    activate(page, field(page, 'strategy-validation-逻辑校验报告').locator('[data-ai-field]'))
    page.locator('#close-ai').focus(); page.keyboard.press('Shift+Tab')
    assert page.evaluate("document.activeElement.closest('#ai-panel') !== null")
    page.keyboard.press('Tab')
    assert page.evaluate("document.activeElement.closest('#ai-panel') !== null")
    page.locator('#ai-open-settings').click()
    expect(page.locator('#ai-panel')).not_to_be_visible()
    expect(page.locator('#ai-settings')).to_be_visible()
    assert page.locator('dialog[open]').count() == 1
    page.locator('#ai-provider').select_option('custom')
    page.locator('#ai-endpoint').fill(ENDPOINT_FIXTURE)
    page.locator('#ai-model').fill('fixture-model-not-live')
    page.locator('#ai-key').fill(KEY_FIXTURE)
    assert not page.locator('#ai-remember-key').is_checked()
    page.locator('#save-ai-preferences').click()
    page.locator('#close-ai-settings').click()
    expect(page.locator('#ai-panel')).to_be_visible()
    assert page.locator('#ai-panel #ai-key, #ai-panel #ai-provider, #ai-panel #ai-endpoint, #ai-panel #ai-model').count() == 0
    calls = []
    def fixture(route):
        if route.request.method == 'OPTIONS':
            route.fulfill(status=204, headers={'access-control-allow-origin': '*', 'access-control-allow-methods': 'POST, OPTIONS', 'access-control-allow-headers': 'Content-Type, Authorization'})
            return
        calls.append(route.request)
        assert route.request.headers.get('authorization') == 'Bearer ' + KEY_FIXTURE
        assert '虚构验收企业' in route.request.post_data
        route.fulfill(status=200, headers={'access-control-allow-origin': '*'}, content_type='application/json', body=json.dumps({'choices': [{'message': {'content': XSS + '\n虚构 AI 校验结果 ' + KEY_FIXTURE}}]}))
    page.route(ENDPOINT_FIXTURE, fixture)
    page.locator('#ai-send').click()
    assert not calls
    approve_global(page)
    page.locator('#ai-send').click()
    expect(page.locator('#ai-apply')).to_be_visible()
    assert len(calls) == 1
    assert KEY_FIXTURE not in page.locator('#ai-result').inner_text()
    safe_preview(page)
    page.once('dialog', lambda dialog: dialog.accept())
    page.locator('#ai-apply').click()
    assert '虚构 AI 校验结果' in field_value(page, 'strategy-validation-逻辑校验报告')
    # Model failure exposes only generic status; no full provider response or Key.
    page.unroute(ENDPOINT_FIXTURE, fixture)
    page.route(ENDPOINT_FIXTURE, lambda route: route.fulfill(status=401, headers={'access-control-allow-origin': '*', 'access-control-allow-headers': 'Content-Type, Authorization'}, content_type='application/json', body=json.dumps({'error': {'message': KEY_FIXTURE + '<script>bad</script>'}})))
    page.locator('#ai-send').click()
    expect(page.locator('#ai-result')).to_contain_text('HTTP 401')
    assert KEY_FIXTURE not in page.locator('#ai-result').inner_text()
    before_errors = current_draft(page)
    page.unroute(ENDPOINT_FIXTURE)
    page.route(ENDPOINT_FIXTURE, lambda route: route.fulfill(status=200, headers={'access-control-allow-origin': '*'}, content_type='application/json', body='{"choices":[]}'))
    page.locator('#ai-send').click()
    expect(page.locator('#ai-result')).to_contain_text('接口格式不兼容')
    assert current_draft(page) == before_errors
    page.unroute(ENDPOINT_FIXTURE)
    page.route(ENDPOINT_FIXTURE, lambda route: route.abort('failed'))
    page.locator('#ai-send').click()
    expect(page.locator('#ai-result')).to_contain_text('网络、CORS')
    assert current_draft(page) == before_errors
    # Closing a pending request cancels the wait; a late response cannot update/apply.
    page.unroute(ENDPOINT_FIXTURE)
    # Explicit in-browser fixture ignores abort and delivers late, exercising the epoch
    # guard independently of the browser's successful network cancellation.
    page.evaluate("""endpoint => {
        window.__originalFixtureFetch = window.fetch;
        window.fetch = (url, options) => {
            if (url !== endpoint) return window.__originalFixtureFetch(url, options);
            options.signal.addEventListener('abort', () => { window.__fixtureAborted = true; });
            return new Promise(resolve => { window.__resolveFixtureReply = () => resolve(new Response(
                JSON.stringify({choices:[{message:{content:'fixture-late-answer-must-be-ignored'}}]}),
                {status:200, headers:{'Content-Type':'application/json'}})); });
        };
    }""", ENDPOINT_FIXTURE)
    page.locator('#ai-send').click()
    expect(page.locator('#ai-cancel')).to_be_enabled()
    page.keyboard.press('Escape')
    expect(page.locator('#ai-panel')).not_to_be_visible()
    assert page.evaluate('window.__fixtureAborted === true')
    page.locator('#open-ai').click()
    expect(page.locator('#ai-cancel')).to_be_disabled()
    page.evaluate("() => {window.__resolveFixtureReply(); window.fetch = window.__originalFixtureFetch;}")
    expect(page.locator('#ai-result')).not_to_contain_text('fixture-late-answer-must-be-ignored')
    expect(page.locator('#ai-apply')).not_to_be_visible()
    assert current_draft(page) == before_errors
    page.locator('#close-ai').click()
    # Export actual downloaded files, including Word HTML with safe rich content.
    structured_path = exported(page, '#export-json', directory)
    structured = json.loads(structured_path.read_text())
    assert len(structured['steps']) == 15 and structured['metadata']['completion']['strategy-validation-completed'] == 'true'
    assert '虚构 AI 校验结果' in structured['metadata']['validationReport']['content']
    for selector in ('#export-markdown', '#export-word'):
        path = exported(page, selector, directory)
        text = path.read_text()
        assert '虚构验收企业' in text and '虚构第二行差距' in text
        assert KEY_FIXTURE not in text
        if selector == '#export-word':
            assert path.suffix == '.doc'
            audit = SafeHTML(); audit.feed(text)
    assert KEY_FIXTURE not in structured_path.read_text()
    assert KEY_FIXTURE not in page.evaluate('JSON.stringify(localStorage)')
    flat = {f'{step["id"]}-{name}': value for step in structured['steps'] for name, value in step['data'].items()}
    flat.update(structured['metadata']['completion'])
    flat_path = Path(directory) / 'fixture-flat.json'
    flat_path.write_text(json.dumps(flat, ensure_ascii=False))
    # Both shapes enter through the actual native file chooser. No direct state injection.
    for path in (flat_path, structured_path):
        page.locator('[data-step="company-info"]').click()
        write_editor(page, 'company-info-企业名称', '临时覆盖值')
        page.once('dialog', lambda dialog: dialog.accept())
        chooser_import(page, path)
        expect(page.locator('#tool-message')).to_have_text('导入成功。')
        assert field_value(page, 'company-info-企业名称') == '虚构验收企业'
        page.locator('[data-step="gap"]').click()
        assert field(page, 'gap-业绩差距').locator('textarea[data-row="1"][data-column="4"]').input_value() == '虚构第二行差距'
        page.locator('[data-step="strategy-validation"]').click()
        safe_preview(page)
    for name, body in [('bad.json', '{bad'), ('prototype.json', '{"__proto__":{"polluted":true}}'), ('wrong-table.json', '{"gap-业绩差距":[[1]]}'), ('oversized.json', ' ' * (4 * 1024 * 1024 + 1)), ('unsupported.docx', 'not-a-docx')]:
        path = Path(directory) / name; path.write_text(body)
        before = current_draft(page)
        chooser_import(page, path)
        expect(page.locator('#tool-message')).to_contain_text('导入失败')
        assert current_draft(page) == before
    # Resize never deletes or reinitializes the existing desktop draft.
    before = current_draft(page)
    for width in (1024, 1440):
        page.set_viewport_size({'width': width, 'height': 1000})
        page.locator('[data-step="company-info"]').click()
        expect(field(page, 'company-info-主营业务').locator('.simple-input')).to_be_visible()
        no_overflow(page); screenshot(page, f'workspace-{width}.png')
        if width == 1024:
            # Seed a known real field/control for each revisit, independent of application memory.
            expected_focus = {}
            for nav in page.locator('#step-nav button').all():
                nav.click()
                first = page.locator('#step-content [data-field]').first
                target_id = first.get_attribute('data-field')
                if first.locator('.CodeMirror').count():
                    first.locator('.CodeMirror').click()
                    expected_focus[nav.get_attribute('data-step')] = (target_id, False)
                else:
                    control = first.locator('input:not([type="file"]), textarea').first
                    control.click()
                    expected_focus[nav.get_attribute('data-step')] = (target_id, control.get_attribute('data-row') is not None)
            for nav in page.locator('#step-nav button').all():
                nav.click()
                expected_id, is_table = expected_focus[nav.get_attribute('data-step')]
                actual_id = page.evaluate("document.activeElement.closest('[data-field]')?.dataset.field")
                assert actual_id == expected_id, (expected_id, actual_id)
                if is_table:
                    assert page.evaluate("[document.activeElement.dataset.row, document.activeElement.dataset.column]") == ['0', '0']
                no_overflow(page)
                footer = page.locator('.step-pager').bounding_box()
                assert footer['y'] + footer['height'] <= 1000
            page.locator('[data-step="company-info"]').click()
    vendor_count = len([u for u in requests if '/vendor/' in u])
    page.set_viewport_size({'width': 390, 'height': 900})
    expect(page.locator('#companion')).to_be_visible()
    expect(page.locator('#workspace')).not_to_be_visible()
    no_overflow(page)
    page.set_viewport_size({'width': 1440, 'height': 1000})
    expect(page.locator('#workspace')).to_be_visible()
    assert current_draft(page) == before
    assert len([u for u in requests if '/vendor/' in u]) == vendor_count
    ai_requests_before_reload = sum(u == ENDPOINT_FIXTURE for u in requests)
    page.reload(wait_until='networkidle')
    expect(page.locator('#workspace')).to_be_visible()
    page.locator('#open-ai').click()
    assert not page.locator('#ai-consent').is_checked()
    page.locator('#ai-open-settings').click()
    assert page.locator('#ai-key').input_value() == ''
    assert page.locator('#ai-endpoint').input_value() == ENDPOINT_FIXTURE
    assert sum(u == ENDPOINT_FIXTURE for u in requests) == ai_requests_before_reload
    assert all(urlsplit(u).netloc == urlsplit(base).netloc or u == ENDPOINT_FIXTURE for u in requests), requests
    assert not errors and not assets, (errors, assets)
    page.close()


def approve_global(page):
    # Confirm once in the visible global dialog, never inside a step.
    if page.locator('#ai-consent').is_checked():
        return
    if page.locator('#ai-settings').is_visible():
        page.locator('#ai-consent').check()
        return
    page.locator('#ai-open-settings').click()
    expect(page.locator('#ai-settings #ai-disclosure')).to_contain_text('规划全文、已有校验报告')
    page.locator('#ai-consent').check()
    page.locator('#close-ai-settings').click()


def configure_global(page, remember=False):
    # Call with the visible global dialog. Only explicit fake credentials are used.
    page.locator('#ai-provider').select_option('custom')
    page.locator('#ai-endpoint').fill(ENDPOINT_FIXTURE)
    page.locator('#ai-model').fill('fixture-model-not-live')
    page.locator('#ai-key').fill(KEY_FIXTURE)
    page.locator('#ai-remember-key').set_checked(remember)
    page.locator('#ai-consent').check()
    page.locator('#save-ai-preferences').click()


def remembered_raw(page):
    return page.evaluate('(key) => localStorage.getItem(key)', REMEMBERED)


def check_global_ai(browser, base, directory):
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    page = context.new_page()
    requests, errors, assets = watch(page, base)
    calls = []
    def fixture(route):
        if route.request.method == 'OPTIONS':
            route.fulfill(status=204, headers={'access-control-allow-origin': '*', 'access-control-allow-methods': 'POST, OPTIONS', 'access-control-allow-headers': 'Content-Type, Authorization'})
            return
        assert route.request.headers.get('authorization') == 'Bearer ' + KEY_FIXTURE
        assert KEY_FIXTURE not in route.request.url and KEY_FIXTURE not in route.request.post_data
        assert len(json.loads(route.request.post_data)['messages']) == 2
        calls.append(route.request)
        route.fulfill(status=200, headers={'access-control-allow-origin': '*'}, content_type='application/json', body=json.dumps({'choices': [{'message': {'content': '虚构全局建议 ' + KEY_FIXTURE}}]}))
    page.route(ENDPOINT_FIXTURE, fixture)
    page.goto(base + '/apps/deepblm.html?internal_test=1', wait_until='networkidle')
    expect(page.locator('#open-ai-settings')).to_have_text('AI 设置 · 未配置')
    page.locator('#open-ai-settings').click()
    assert not page.locator('#ai-remember-key').is_checked()
    assert page.locator('#ai-key').get_attribute('type') == 'password'
    expect(page.locator('#ai-storage-disclosure')).to_contain_text('明文')
    bounds = page.locator('#ai-settings').bounding_box()
    assert 0 <= bounds['y'] and bounds['y'] + bounds['height'] <= 1000
    page.locator('#close-ai-settings').focus(); page.keyboard.press('Shift+Tab')
    assert page.evaluate("document.activeElement.closest('#ai-settings') !== null")
    page.keyboard.press('Tab')
    expect(page.locator('#close-ai-settings')).to_be_focused()
    page.keyboard.press('Escape')
    expect(page.locator('#open-ai-settings')).to_be_focused()
    expect(page.locator('dialog[open]')).to_have_count(0)
    page.locator('#open-ai-settings').click()
    configure_global(page)
    assert remembered_raw(page) is None
    assert KEY_FIXTURE not in page.evaluate('JSON.stringify(localStorage)')
    assert not calls
    page.locator('#close-ai-settings').click()
    expect(page.locator('#open-ai-settings')).to_have_text('AI 设置 · 已配置')
    # Configure once, then use the real field action in every one of the 15 steps.
    steps = page.locator('#step-nav button').count()
    assert steps == 15
    for i in range(steps):
        page.locator('#step-nav button').nth(i).click()
        activate(page, page.locator('[data-ai-field]').first)
        assert page.locator('#ai-panel #ai-key, #ai-panel #ai-provider, #ai-panel #ai-endpoint, #ai-panel #ai-model, #ai-panel #save-ai-preferences').count() == 0
        expect(page.locator('#ai-config-status')).not_to_be_visible()
        expect(page.locator('#ai-open-settings')).not_to_be_visible()
        expect(page.locator('#ai-panel #ai-disclosure, #ai-panel #ai-destination, #ai-panel #ai-consent')).to_have_count(0)
        assert not any(text in page.locator('#ai-panel').inner_text() for text in ('API', 'Key', '模型 ID', 'CORS', '全局设置'))
        page.locator('#ai-send').click()
        expect(page.locator('#ai-apply')).to_be_visible()
        expect(page.locator('#ai-result')).to_contain_text('虚构全局建议')
        assert KEY_FIXTURE not in page.locator('#ai-result').inner_text()
        assert len(calls) == i + 1
        page.locator('#close-ai').click()
    # Safe default memory mode loses only its Key at reload, not the global config.
    page.reload(wait_until='networkidle')
    assert len(calls) == 15
    page.locator('#open-ai-settings').click()
    assert page.locator('#ai-key').input_value() == ''
    assert not page.locator('#ai-remember-key').is_checked()
    assert page.locator('#ai-endpoint').input_value() == ENDPOINT_FIXTURE
    page.locator('#ai-key').fill(KEY_FIXTURE)
    page.locator('#ai-remember-key').check()
    page.locator('#save-ai-preferences').click()
    record = json.loads(remembered_raw(page))
    assert record == {'version': 1, 'remembered': True, 'provider': 'custom', 'endpoint': ENDPOINT_FIXTURE, 'key': KEY_FIXTURE}
    assert 'consent' not in page.evaluate('JSON.stringify(localStorage)')
    expect(page.locator('#ai-remember-status')).to_contain_text('已在此浏览器记住')
    page.locator('#close-ai-settings').click()
    # Import and step reset do not erase global settings.
    incoming = Path(directory) / 'global-settings-draft.json'
    incoming.write_text(json.dumps({'company-info-企业名称': '虚构全局配置验收企业'}))
    before = remembered_raw(page)
    page.once('dialog', lambda dialog: dialog.accept())
    chooser_import(page, incoming)
    page.once('dialog', lambda dialog: dialog.accept())
    activate(page, '#reset-step')
    assert remembered_raw(page) == before
    for selector in ('#export-json', '#export-markdown', '#export-word'):
        assert KEY_FIXTURE not in exported(page, selector, directory).read_text()
    page.reload(wait_until='networkidle')
    page.locator('#open-ai').click()
    assert not page.locator('#ai-consent').is_checked()
    page.locator('#ai-send').click(); assert len(calls) == 15
    expect(page.locator('#ai-message')).to_contain_text('请先完成全局设置')
    page.locator('#close-ai').click()
    page.locator('#open-ai-settings').click()
    assert page.locator('#ai-key').input_value() == KEY_FIXTURE
    assert page.locator('#ai-provider').input_value() == 'custom'
    assert page.locator('#ai-remember-key').is_checked()
    page.locator('#close-ai-settings').click()
    # A new page in the same browser context restores the explicit record, never consent.
    other = context.new_page()
    other_requests, other_errors, other_assets = watch(other, base)
    other.goto(base + '/apps/deepblm.html?internal_test=1', wait_until='networkidle')
    other.locator('#open-ai').click()
    assert not other.locator('#ai-consent').is_checked()
    expect(other.locator('#ai-open-settings')).to_be_visible()
    expect(other.locator('#ai-config-status')).to_contain_text('请先完成全局设置')
    other.locator('#close-ai').click()
    other.locator('#open-ai-settings').click()
    assert other.locator('#ai-key').input_value() == KEY_FIXTURE
    assert not any(u == ENDPOINT_FIXTURE for u in other_requests)
    # A different tab changes only the saved endpoint, leaving a stale secret record.
    # Current credentials are dropped and reload cannot bind that secret to the new URL.
    other.evaluate('''({key, endpoint}) => {
        const config = JSON.parse(localStorage.getItem(key));
        config.endpoint = endpoint; localStorage.setItem(key, JSON.stringify(config));
    }''', {'key': PREFERENCES, 'endpoint': ENDPOINT_FIXTURE + '/another-destination'})
    expect(page.locator('#open-ai-settings')).to_have_text('AI 设置 · 未配置')
    other.reload(wait_until='networkidle')
    other.locator('#open-ai-settings').click()
    assert other.locator('#ai-key').input_value() == ''
    assert not other.locator('#ai-remember-key').is_checked()
    configure_global(other, remember=True)
    # Uncheck + save removes the actual secret record and invalidates other-tab credentials.
    other.locator('#ai-remember-key').uncheck()
    other.locator('#save-ai-preferences').click()
    assert remembered_raw(other) is None
    expect(page.locator('#open-ai-settings')).to_have_text('AI 设置 · 未配置')
    other.reload(wait_until='networkidle')
    other.locator('#open-ai-settings').click()
    assert other.locator('#ai-key').input_value() == ''
    configure_global(other, remember=True)
    other.locator('#forget-key').click()
    assert remembered_raw(other) is None and other.locator('#ai-key').input_value() == ''
    other.reload(wait_until='networkidle')
    other.locator('#open-ai-settings').click()
    assert other.locator('#ai-key').input_value() == ''
    configure_global(other, remember=True)
    other.locator('#close-ai-settings').click()
    other.evaluate("localStorage.setItem('sibling-app-fixture', 'keep'); localStorage.setItem('da-ai-config', 'sibling-fixture-never-read')")
    other.once('dialog', lambda dialog: dialog.accept())
    activate(other, '#clear-local')
    assert remembered_raw(other) is None
    assert other.evaluate("localStorage.getItem('sibling-app-fixture')") == 'keep'
    assert other.evaluate("localStorage.getItem('da-ai-config')") == 'sibling-fixture-never-read'
    other.locator('#open-ai-settings').click()
    assert other.locator('#ai-key').input_value() == ''
    other.locator('#close-ai-settings').click()
    # Transition preserves target/question; destination changes cannot reuse an old Key/result.
    page.locator('#step-nav button').first.click()
    activate(page, page.locator('[data-ai-field]').first)
    page.locator('#ai-question').fill('虚构需要保留的问题')
    target = page.locator('#ai-target').inner_text()
    page.locator('#ai-open-settings').click()
    configure_global(page)
    page.keyboard.press('Escape')
    expect(page.locator('#ai-question')).to_be_focused()
    expect(page.locator('#ai-open-settings')).not_to_be_visible()
    assert page.locator('#ai-target').inner_text() == target
    assert page.locator('#ai-question').input_value() == '虚构需要保留的问题'
    assert page.locator('dialog[open]').count() == 1
    approve_global(page); page.locator('#ai-send').click()
    expect(page.locator('#ai-apply')).to_be_visible()
    count = len(calls)
    # Opening global settings cancels an in-flight request; even a fixture that
    # ignores AbortSignal cannot resurrect its result after configuration changes.
    page.evaluate('''endpoint => {
        window.__originalGlobalFixtureFetch = window.fetch;
        window.fetch = (url, options) => {
            if (url !== endpoint) return window.__originalGlobalFixtureFetch(url, options);
            options.signal.addEventListener('abort', () => {window.__globalFixtureAborted = true;});
            return new Promise(resolve => {window.__resolveGlobalFixture = () => resolve(new Response(
                JSON.stringify({choices:[{message:{content:'fixture-old-global-response'}}]}),
                {status:200, headers:{'Content-Type':'application/json'}}));});
        };
    }''', ENDPOINT_FIXTURE)
    page.locator('#ai-send').click()
    expect(page.locator('#ai-cancel')).to_be_enabled()
    page.locator('#close-ai').click()
    page.locator('#open-ai-settings').click()
    assert page.evaluate('window.__globalFixtureAborted === true')
    page.locator('#ai-endpoint').fill(ENDPOINT_FIXTURE + '/changed')
    assert page.locator('#ai-key').input_value() == ''
    page.locator('#save-ai-preferences').click()
    page.locator('#close-ai-settings').click()
    activate(page, page.locator('[data-ai-field]').first)
    assert not page.locator('#ai-consent').is_checked()
    expect(page.locator('#ai-apply')).not_to_be_visible()
    expect(page.locator('.ai-result-card')).to_have_attribute('data-state', 'empty')
    page.evaluate('''() => {window.__resolveGlobalFixture(); window.fetch = window.__originalGlobalFixtureFetch;}''')
    expect(page.locator('#ai-result')).not_to_contain_text('fixture-old-global-response')
    request_count = len(requests)
    approve_global(page); page.locator('#ai-send').click()
    expect(page.locator('#ai-message')).to_contain_text('请先完成全局设置')
    assert len(calls) == count and len(requests) == request_count
    page.locator('#ai-open-settings').click()
    page.locator('#ai-key').fill(KEY_FIXTURE)
    page.locator('#ai-provider').select_option('openai')
    assert page.locator('#ai-key').input_value() == ''
    page.locator('#ai-model').fill('fixture-model-not-live')
    page.locator('#save-ai-preferences').click()
    page.locator('#close-ai-settings').click()
    assert not page.locator('#ai-consent').is_checked()
    expect(page.locator('#ai-apply')).not_to_be_visible()
    approve_global(page); page.locator('#ai-send').click()
    expect(page.locator('#ai-message')).to_contain_text('请先完成全局设置')
    assert len(calls) == count and len(requests) == request_count
    page.locator('#ai-open-settings').click()
    # Both dialogs close on mobile resize, without a hidden stacked modal.
    page.set_viewport_size({'width': 390, 'height': 900})
    expect(page.locator('dialog[open]')).to_have_count(0)
    page.set_viewport_size({'width': 1440, 'height': 1000})
    page.locator('#open-ai').click()
    page.set_viewport_size({'width': 390, 'height': 900})
    expect(page.locator('dialog[open]')).to_have_count(0)
    assert all(KEY_FIXTURE not in u for u in requests + other_requests)
    assert KEY_FIXTURE not in page.locator('body').inner_text()
    assert not errors and not assets and not other_errors and not other_assets, (errors, assets, other_errors, other_assets)
    context.close()


def check_composer_draft_boundaries(browser, base, directory):
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    requests, errors, assets = watch(page, base)
    page.goto(base + '/apps/deepblm.html?internal_test=1', wait_until='networkidle')
    write_editor(page, 'company-info-主营业务', '虚构旧业务')
    field(page, 'company-info-主营业务').locator('[data-ai-field]').click()
    page.locator('#ai-open-settings').click(); configure_global(page)
    page.locator('#close-ai-settings').click()
    page.locator('#ai-question').fill('虚构旧口径，不应传到新草稿')
    page.locator('[data-ai-action="inspect"]').click()
    page.locator('#close-ai').click()
    incoming = Path(directory) / 'composer-new-draft.json'
    incoming.write_text(json.dumps({'company-info-主营业务': '虚构新业务'}))
    page.once('dialog', lambda dialog: dialog.dismiss()); chooser_import(page, incoming)
    field(page, 'company-info-主营业务').locator('[data-ai-field]').click()
    expect(page.locator('#ai-question')).to_have_value('虚构旧口径，不应传到新草稿')
    expect(page.locator('[data-ai-action="inspect"]')).to_have_attribute('aria-pressed', 'true')
    page.locator('#close-ai').click()
    bad = Path(directory) / 'composer-bad-draft.json'; bad.write_text('invalid')
    chooser_import(page, bad)
    expect(page.locator('#tool-message')).to_contain_text('导入失败')
    field(page, 'company-info-主营业务').locator('[data-ai-field]').click()
    expect(page.locator('#ai-question')).to_have_value('虚构旧口径，不应传到新草稿')
    page.locator('#ai-discussion').click()
    page.locator('#ai-question').fill('虚构旧企业讨论')
    page.locator('#close-ai').click()
    page.locator('[data-step="gap"]').click(); page.locator('#open-ai').click()
    page.locator('#ai-discussion').click(); page.locator('#ai-question').fill('虚构其他步骤要求')
    page.locator('#close-ai').click(); page.locator('[data-step="company-info"]').click()
    page.once('dialog', lambda dialog: dialog.dismiss()); activate(page, '#reset-step')
    field(page, 'company-info-主营业务').locator('[data-ai-field]').click()
    expect(page.locator('#ai-question')).to_have_value('虚构旧口径，不应传到新草稿')
    page.locator('#close-ai').click()
    page.once('dialog', lambda dialog: dialog.accept()); activate(page, '#reset-step')
    field(page, 'company-info-主营业务').locator('[data-ai-field]').click()
    expect(page.locator('#ai-question')).to_have_value('')
    expect(page.locator('[data-ai-action="draft"]')).to_have_attribute('aria-pressed', 'true')
    page.locator('#ai-discussion').click(); expect(page.locator('#ai-question')).to_have_value('')
    page.locator('#close-ai').click(); page.locator('[data-step="gap"]').click()
    page.locator('#open-ai').click(); page.locator('#ai-discussion').click()
    expect(page.locator('#ai-question')).to_have_value('虚构其他步骤要求')
    page.locator('#close-ai').click(); page.locator('[data-step="company-info"]').click()
    field(page, 'company-info-主营业务').locator('[data-ai-field]').click()
    page.locator('#ai-question').fill('虚构待被导入清除的要求')
    page.locator('[data-ai-action="inspect"]').click(); page.locator('#close-ai').click()
    page.once('dialog', lambda dialog: dialog.accept()); chooser_import(page, incoming)
    field(page, 'company-info-主营业务').locator('[data-ai-field]').click()
    expect(page.locator('#ai-question')).to_have_value('')
    expect(page.locator('[data-ai-action="improve"]')).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('#ai-snapshot-content')).to_have_text('虚构新业务')
    page.locator('#close-ai').click(); page.locator('[data-step="gap"]').click()
    page.locator('#open-ai').click(); page.locator('#ai-discussion').click()
    expect(page.locator('#ai-question')).to_have_value('')
    page.locator('#close-ai').click()
    # A legal long source must be included once, not duplicated into the budget.
    page.locator('[data-step="revision"]').click()
    long_source = 'x' * 95000
    write_editor(page, 'revision-修改建议列表', long_source)
    field(page, 'revision-修改建议列表').locator('[data-ai-field]').click()
    page.locator('#ai-snapshot summary').click()
    page.locator('#ai-snapshot-content').focus()
    expect(page.locator('#ai-snapshot-content')).to_be_focused()
    page.locator('#ai-snapshot-content').press('End')
    page.wait_for_function("() => document.querySelector('#ai-snapshot-content').scrollTop > 0")
    calls = []
    def fixture(route):
        if route.request.method == 'OPTIONS':
            route.fulfill(status=204, headers={'access-control-allow-origin': '*', 'access-control-allow-methods': 'POST, OPTIONS', 'access-control-allow-headers': 'Content-Type, Authorization'})
            return
        calls.append(json.loads(route.request.post_data))
        route.fulfill(status=200, headers={'access-control-allow-origin': '*'}, content_type='application/json', body=json.dumps({'choices': [{'message': {'content': '虚构长文建议'}}]}))
    page.route(ENDPOINT_FIXTURE, fixture)
    page.locator('#ai-send').click(); expect(page.locator('.ai-result-card')).to_have_attribute('data-state', 'success')
    assert len(calls) == 1
    payload = '\n'.join(m['content'] for m in calls[0]['messages'])
    assert payload.count(long_source) == 1
    assert '虚构旧口径' not in payload and '虚构其他步骤要求' not in payload
    page.locator('#step-content').evaluate('e => {e.scrollTop = 100;}')
    saved_scroll = page.locator('#step-content').evaluate('e => e.scrollTop')
    page.once('dialog', lambda dialog: dialog.accept()); page.locator('#ai-apply').click()
    geometry = page.locator('#step-content').evaluate('e => ({top:e.scrollTop,max:e.scrollHeight-e.clientHeight})')
    assert abs(geometry['top'] - min(saved_scroll, geometry['max'])) <= 1
    page.locator('#close-ai').click()
    expect(field(page, 'revision-修改建议列表').locator('[data-ai-field]')).to_be_focused()
    assert field_value(page, 'revision-修改建议列表') == '虚构长文建议'
    assert not errors and not assets, (errors, assets)
    page.close()


def check_writing_composer(browser, base, directory):
    context = browser.new_context(viewport={'width': 1440, 'height': 900})
    page = context.new_page()
    requests, errors, assets = watch(page, base)
    calls = []
    reply = {'content': '虚构改进稿：设备服务的客户依据待补充。'}

    def fixture(route):
        if route.request.method == 'OPTIONS':
            route.fulfill(status=204, headers={'access-control-allow-origin': '*', 'access-control-allow-methods': 'POST, OPTIONS', 'access-control-allow-headers': 'Content-Type, Authorization'})
            return
        assert route.request.headers.get('authorization') == 'Bearer ' + KEY_FIXTURE
        calls.append(json.loads(route.request.post_data))
        route.fulfill(status=200, headers={'access-control-allow-origin': '*'}, content_type='application/json', body=json.dumps({'choices': [{'message': {'content': reply['content']}}]}))

    page.route(ENDPOINT_FIXTURE, fixture)
    page.goto(base + '/apps/deepblm.html?internal_test=1', wait_until='networkidle')
    write_editor(page, 'company-info-企业名称', '虚构写作验收')
    # Text import is still a separate, genuine native file action.
    incoming = Path(directory) / 'fixture-writing.txt'
    original = '虚构设备服务；客户数量待核实。<img src=x onerror=alert(1)>'
    incoming.write_text(original, encoding='utf-8')
    business = field(page, 'company-info-主营业务')
    with page.expect_file_chooser() as chooser:
        business.get_by_role('button', name='导入文本', exact=True).click()
    chooser.value.set_files(str(incoming))
    expect(business.locator('.simple-input')).to_have_value(original)
    direct = business.locator('[data-ai-field]')
    expect(direct).to_have_text('AI 帮写')
    assert direct.locator('xpath=ancestor::details').count() == 0
    direct.click()
    expect(page.locator('#ai-open-settings')).to_be_focused()
    expect(page.locator('#ai-question')).to_have_value('')
    expect(page.locator('#ai-target')).to_have_text('企业信息 / 主营业务')
    expect(page.locator('#ai-snapshot-content')).to_have_text(original)
    assert page.locator('#ai-snapshot-content input, #ai-snapshot-content textarea, #ai-snapshot-content img, #ai-snapshot-content [contenteditable]').count() == 0
    expect(page.locator('[data-ai-action="improve"]')).to_have_attribute('aria-pressed', 'true')
    options = page.locator('#ai-target-select option').evaluate_all('(nodes) => nodes.map(n => n.value)')
    assert options == ['company-info-企业名称', 'company-info-主营业务', 'company-info-行业描述', 'company-info-企业规模', 'company-info-企业现状', 'discussion']
    # Choosing a shortcut is an explicit non-sending action, with exactly one selection.
    for action in ('draft', 'improve', 'inspect'):
        page.locator(f'[data-ai-action="{action}"]').click()
        expect(page.locator(f'[data-ai-action="{action}"]')).to_have_attribute('aria-pressed', 'true')
        assert page.locator('.ai-shortcuts [aria-pressed="true"]').count() == 1
    question = page.locator('#ai-question')
    question.fill('虚构要求：保留不确定性，不补造数据。')
    page.locator('#close-ai').click()
    expect(direct).to_be_focused()
    direct.click()
    expect(question).to_have_value('虚构要求：保留不确定性，不补造数据。')
    expect(page.locator('[data-ai-action="inspect"]')).to_have_attribute('aria-pressed', 'true')
    page.locator('#ai-open-settings').click()
    configure_global(page)
    page.keyboard.press('Escape')
    expect(question).to_be_focused()
    expect(question).to_have_value('虚构要求：保留不确定性，不补造数据。')
    expect(page.locator('#ai-target-select')).to_have_value('company-info-主营业务')
    expect(page.locator('[data-ai-action="inspect"]')).to_have_attribute('aria-pressed', 'true')
    assert page.locator('dialog[open]').count() == 1
    # Repeat with a configured, approved connection so an accidental send is observable.
    for action in ('draft', 'improve', 'inspect'):
        page.locator(f'[data-ai-action="{action}"]').click()
        expect(page.locator(f'[data-ai-action="{action}"]')).to_have_attribute('aria-pressed', 'true')
    page.locator('#close-ai').click()
    direct.click()
    expect(question).to_be_focused()
    expect(question).to_have_value('虚构要求：保留不确定性，不补造数据。')
    assert not calls
    # Target switching clears results, selects a useful default, and isolates user text.
    page.locator('#ai-target-select').select_option('company-info-行业描述')
    expect(question).to_have_value('')
    expect(question).to_have_attribute('placeholder', '对“行业描述”还有什么要求？例如范围、语气或需保留的内容。')
    expect(page.locator('[data-ai-action="draft"]')).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('#ai-snapshot')).to_contain_text('尚未填写')
    assert not calls
    page.locator('#close-ai').click()
    page.locator('#open-ai').click()
    expect(page.locator('#ai-target-select')).to_have_value('company-info-行业描述')
    expect(question).to_be_focused()
    # An empty supplemental box still sends a meaningful schema-aware request.
    before = current_draft(page)
    question.press('Control+Enter')
    expect(page.locator('.ai-result-card')).to_have_attribute('data-state', 'success')
    assert len(calls) == 1
    payload = calls[-1]['messages']
    assert '目标：企业信息 / 行业描述' in payload[1]['content']
    assert '起草可直接填入此字段' in payload[1]['content']
    assert '描述所属行业' in payload[1]['content']
    assert '无；请按上述任务与字段指引处理' in payload[1]['content']
    assert original in json.loads(payload[1]['content'].split('规划上下文：\n', 1)[1].split('\n\n补充要求', 1)[0])['steps'][0]['data']['主营业务']
    assert '不得编造' in payload[0]['content']
    assert current_draft(page) == before
    expect(page.locator('#ai-apply')).to_be_visible()
    page.locator('#ai-target-select').select_option('company-info-主营业务')
    expect(page.locator('.ai-result-card')).to_have_attribute('data-state', 'empty')
    expect(page.locator('#ai-apply')).not_to_be_visible()
    expect(question).to_have_value('虚构要求：保留不确定性，不补造数据。')
    # Critique and discussion responses are visible but never offered as replacement drafts.
    page.locator('#ai-send').click()
    expect(page.locator('.ai-result-card')).to_have_attribute('data-state', 'success')
    assert '问题清单，不改写字段' in calls[-1]['messages'][1]['content']
    expect(page.locator('#ai-apply')).not_to_be_visible()
    assert current_draft(page) == before
    page.locator('#ai-discussion').click()
    expect(page.locator('#ai-target-select')).to_have_value('discussion')
    expect(page.locator('#ai-snapshot')).not_to_be_visible()
    expect(page.locator('#ai-discussion')).to_have_attribute('aria-pressed', 'true')
    assert len(calls) == 2
    page.locator('#ai-send').click()
    expect(page.locator('.ai-result-card')).to_have_attribute('data-state', 'success')
    expect(page.locator('#ai-apply')).not_to_be_visible()
    assert '规划讨论' in calls[-1]['messages'][1]['content']
    assert current_draft(page) == before
    # Plain Enter inserts a newline; IME composition cannot submit either shortcut.
    question.fill('虚构第一行'); question.press('End'); question.press('Enter')
    expect(question).to_have_value('虚构第一行\n')
    count = len(calls)
    question.dispatch_event('compositionstart', {'data': '测'})
    question.press('Control+Enter')
    question.dispatch_event('compositionend', {'data': '测'})
    question.dispatch_event('keydown', {'key': 'Enter', 'metaKey': True, 'isComposing': True})
    question.dispatch_event('keydown', {'key': 'Enter', 'ctrlKey': True, 'keyCode': 229})
    assert len(calls) == count
    question.press('Meta+Enter')
    expect(page.locator('.ai-result-card')).to_have_attribute('data-state', 'success')
    assert len(calls) == count + 1
    page.locator('#close-ai').click()
    for name in ('行业描述', '企业规模', '企业现状'):
        write_editor(page, 'company-info-' + name, '虚构已填写：' + name)
    page.locator('#open-ai').click()
    expect(page.locator('#ai-target-select')).to_have_value('company-info-企业名称')
    page.keyboard.press('Escape')
    expect(page.locator('#open-ai')).to_be_focused()
    # A fixture ignoring abort proves duplicate protection, cancel and target-switch rejection.
    page.locator('[data-step="gap"]').click()
    page.locator('[data-ai-field="gap-业绩差距"]').click()
    expect(page.locator('#ai-snapshot-content th')).to_have_count(5)
    expect(page.locator('#ai-snapshot-content')).to_contain_text('关键指标类别')
    page.evaluate("""endpoint => {
        window.__composerFetch = window.fetch; window.__composerCalls = 0;
        window.fetch = (url, options) => {
            if (url !== endpoint) return window.__composerFetch(url, options);
            window.__composerCalls++;
            options.signal.addEventListener('abort', () => {window.__composerAborted = true;});
            return new Promise(resolve => {window.__composerResolve = () => resolve(new Response(
                JSON.stringify({choices:[{message:{content:'fixture-stale-composer-result'}}]}),
                {status:200, headers:{'Content-Type':'application/json'}}));});
        };
    }""", ENDPOINT_FIXTURE)
    for ending in ('cancel', 'switch'):
        page.evaluate('window.__composerAborted = false')
        page.locator('#ai-send').click()
        expect(page.locator('#ai-send')).to_have_text('生成中…')
        expect(page.locator('#ai-send')).to_be_disabled()
        expect(page.locator('#ai-cancel')).to_be_visible()
        expect(page.locator('.ai-result-card')).to_have_attribute('data-state', 'loading')
        pending_count = page.evaluate('window.__composerCalls')
        question.press('Control+Enter'); question.press('Meta+Enter')
        assert page.evaluate('window.__composerCalls') == pending_count
        if ending == 'cancel':
            page.locator('#ai-cancel').click()
            expect(page.locator('#ai-result')).to_contain_text('已停止等待；已发送内容无法撤回')
        else:
            page.locator('#ai-target-select').select_option('gap-机会差距')
        assert page.evaluate('window.__composerAborted === true')
        expect(page.locator('#ai-cancel')).not_to_be_visible()
        expect(page.locator('#ai-send')).to_have_text('生成建议')
        page.evaluate('''async () => {
            window.__composerResolve();
            await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        }''')
        expect(page.locator('#ai-result')).not_to_contain_text('fixture-stale-composer-result')
        expect(page.locator('#ai-apply')).not_to_be_visible()
    page.evaluate('() => { window.fetch = window.__composerFetch; }')
    page.locator('#ai-target-select').select_option('gap-业绩差距')
    # Invalid table output is rejected atomically before confirmation/application.
    table_before = current_draft(page)
    reply['content'] = '[["错误列数"]]'
    page.locator('#ai-send').click()
    expect(page.locator('#ai-apply')).to_be_visible()
    page.locator('#ai-apply').click()
    expect(page.locator('#ai-message')).to_contain_text('不符合字段或表格结构')
    assert current_draft(page) == table_before
    rows = [['虚构指标类别', '虚构指标', '待核实', '待确认', '待计算']]
    reply['content'] = json.dumps(rows, ensure_ascii=False)
    page.locator('#ai-send').click()
    expect(page.locator('.ai-result-card')).to_have_attribute('data-state', 'success')
    prompt = calls[-1]['messages'][1]['content']
    assert 'JSON 二维字符串数组' in prompt and '每行恰好 5 列' in prompt
    assert '关键指标类别、指标、现状、目标、差距' in prompt
    page.once('dialog', lambda dialog: dialog.dismiss())
    page.locator('#ai-apply').click()
    assert current_draft(page) == table_before
    page.once('dialog', lambda dialog: dialog.accept())
    page.locator('#ai-apply').click()
    expect(page.locator('#ai-snapshot-content td').first).to_have_text(rows[0][0])
    assert field(page, 'gap-业绩差距').locator('textarea[data-column="0"]').input_value() == rows[0][0]
    page.locator('#close-ai').click()
    activate(page, '#undo')
    assert field(page, 'gap-业绩差距').locator('textarea[data-column="0"]').input_value() == ''
    # Long sources and actual results stay within a bounded viewport at both desktop widths.
    for width in (1024, 1440):
        page.set_viewport_size({'width': width, 'height': 800})
        page.locator('[data-step="company-info"]').click()
        long_source = ('虚构原文，待核实。\n' * 60)
        write_editor(page, 'company-info-企业现状', long_source)
        page.locator('[data-ai-field="company-info-企业现状"]').click()
        assert page.locator('#ai-snapshot').get_attribute('open') is None
        page.locator('#ai-snapshot summary').click()
        expect(page.locator('#ai-snapshot-content')).to_have_text(long_source.strip())
        reply['content'] = ('虚构改进结果，数据待核实。\n\n' * 60)
        page.locator('#ai-send').click()
        expect(page.locator('.ai-result-card')).to_have_attribute('data-state', 'success')
        bounds = page.locator('#ai-panel').bounding_box()
        assert bounds['x'] >= 0 and bounds['x'] + bounds['width'] <= width
        assert bounds['y'] >= 0 and bounds['y'] + bounds['height'] <= 800
        assert page.locator('.ai-scroll').evaluate('n => n.scrollHeight > n.clientHeight')
        question.scroll_into_view_if_needed()
        screenshot(page, f'writing-composer-{width}.png')
        page.locator('#ai-apply').scroll_into_view_if_needed()
        screenshot(page, f'writing-result-{width}.png')
        page.keyboard.press('Escape')
        expect(page.locator('[data-ai-field="company-info-企业现状"]')).to_be_focused()
        no_overflow(page)
    # No supplemental prompts enter any persistent storage, and reload never sends.
    assert '虚构要求：保留不确定性' not in page.evaluate('JSON.stringify(localStorage)')
    count = len(calls)
    page.reload(wait_until='networkidle')
    page.locator('[data-ai-field="company-info-主营业务"]').click()
    expect(question).to_have_value('')
    assert len(calls) == count
    assert not errors and not assets, (errors, assets)
    assert all(urlsplit(u).netloc == urlsplit(base).netloc or u == ENDPOINT_FIXTURE for u in requests)
    context.close()


def check_credential_storage_failures(browser, base, directory):
    config = {'provider': 'custom', 'endpoint': ENDPOINT_FIXTURE, 'model': 'fixture-model-not-live'}
    valid = {'version': 1, 'remembered': True, 'provider': 'custom', 'endpoint': ENDPOINT_FIXTURE, 'key': KEY_FIXTURE}
    bad_records = ['{broken', ' ' * 32769, 'null', json.dumps({'apiKey': KEY_FIXTURE}),
                   json.dumps({**valid, 'remembered': False}), json.dumps({**valid, 'extra': XSS}),
                   json.dumps({**valid, 'endpoint': ENDPOINT_FIXTURE + '/other'}),
                   json.dumps({**valid, 'provider': 'openai'}), json.dumps({**valid, '__proto__': {'polluted': True}})]
    for raw in bad_records:
        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        page = context.new_page()
        requests, errors, assets = watch(page, base)
        page.goto(base + '/apps/deepblm.html?internal_test=1', wait_until='networkidle')
        page.evaluate('''({raw, config, remembered, preferences}) => {
            localStorage.setItem(remembered, raw); localStorage.setItem(preferences, JSON.stringify(config));
        }''', {'raw': raw, 'config': config, 'remembered': REMEMBERED, 'preferences': PREFERENCES})
        page.reload(wait_until='networkidle')
        expect(page.locator('#tool-message')).to_contain_text('记忆 Key 无法读取')
        page.locator('#open-ai-settings').click()
        assert page.locator('#ai-key').input_value() == ''
        assert not page.locator('#ai-remember-key').is_checked()
        page.locator('#close-ai-settings').click()
        write_editor(page, 'company-info-企业名称', '虚构异常记忆仍可编辑')
        assert '虚构异常记忆仍可编辑' in current_draft(page)
        assert KEY_FIXTURE not in exported(page, '#export-json', directory).read_text()
        assert remembered_raw(page) == raw  # Invalid records are neither migrated nor overwritten.
        safe_preview(page)
        assert all(urlsplit(u).netloc == urlsplit(base).netloc for u in requests)
        assert not errors and not assets, (errors, assets)
        context.close()
    # Even a valid-looking HTML fixture secret is only a password value, never DOM markup.
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    page = context.new_page(); requests, errors, assets = watch(page, base)
    page.goto(base + '/apps/deepblm.html?internal_test=1', wait_until='networkidle')
    html_key = '<img/src=x/onerror=window.__deepblmXSS=1>'
    page.evaluate('''({record, config, remembered, preferences, draft}) => {
        localStorage.setItem(remembered, JSON.stringify(record)); localStorage.setItem(preferences, JSON.stringify(config));
        localStorage.setItem(draft, '{broken');
    }''', {'record': {**valid, 'key': html_key}, 'config': config, 'remembered': REMEMBERED, 'preferences': PREFERENCES, 'draft': DRAFT})
    page.reload(wait_until='networkidle')
    recovery = exported(page, '#export-recovery', directory).read_text()
    assert REMEMBERED not in recovery and html_key not in recovery and KEY_FIXTURE not in recovery
    page.locator('#open-ai-settings').click()
    assert page.locator('#ai-key').input_value() == html_key
    assert html_key not in page.locator('body').inner_text()
    safe_preview(page)
    assert not errors and not assets, (errors, assets)
    context.close()
    # Failed writes/deletes must not forge a remembered/forgotten indicator.
    for mode in ('denied', 'quota', 'delete'):
        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        if mode == 'denied':
            context.add_init_script("Object.defineProperty(window, 'localStorage', {get() {throw new DOMException('fixture-only denied', 'SecurityError');}})")
        page = context.new_page(); requests, errors, assets = watch(page, base)
        page.goto(base + '/apps/deepblm.html?internal_test=1', wait_until='networkidle')
        page.locator('#open-ai-settings').click()
        if mode == 'delete':
            configure_global(page, remember=True)
            page.evaluate('''key => {
                const original = Storage.prototype.removeItem;
                Storage.prototype.removeItem = function(k) {
                    if (k === key) throw new DOMException('fixture-only denied delete', 'SecurityError');
                    return original.call(this, k);
                };
            }''', REMEMBERED)
            page.locator('#ai-remember-key').uncheck(); page.locator('#save-ai-preferences').click()
            expect(page.locator('#ai-settings-message')).to_contain_text('未确认已忘记')
            assert remembered_raw(page) is not None
            page.locator('#forget-key').click()
            expect(page.locator('#ai-settings-message')).to_contain_text('未确认已忘记')
            assert page.locator('#ai-key').input_value() == ''
        else:
            if mode == 'quota':
                page.evaluate('''key => {
                    const original = Storage.prototype.setItem;
                    Storage.prototype.setItem = function(k, v) {
                        if (k === key) throw new DOMException('fixture-only quota', 'QuotaExceededError');
                        return original.call(this, k, v);
                    };
                }''', REMEMBERED)
            if mode == 'denied': page.once('dialog', lambda dialog: dialog.accept())
            configure_global(page, remember=True)
            expect(page.locator('#ai-settings-message')).to_contain_text('浏览器')
            assert not page.locator('#ai-remember-key').is_checked()
            expect(page.locator('#ai-remember-status')).not_to_contain_text('已在此浏览器记住')
            if mode == 'quota': assert remembered_raw(page) is None
        page.locator('#close-ai-settings').click()
        write_editor(page, 'company-info-企业名称', '虚构存储失败内存草稿')
        output = exported(page, '#export-json', directory).read_text()
        assert '虚构存储失败内存草稿' in output and KEY_FIXTURE not in output
        if mode == 'delete':
            page.once('dialog', lambda dialog: dialog.accept())
            activate(page, '#clear-local')
            expect(page.locator('#tool-message')).to_contain_text('未确认全部删除')
            assert remembered_raw(page) is not None
        assert all(urlsplit(u).netloc == urlsplit(base).netloc for u in requests)
        assert not errors and not assets, (errors, assets)
        context.close()


def check_storage(browser, base, directory):
    legacy = 'blm-strategy-data'
    cases = [(legacy, None), (legacy, ''), (legacy, '{broken'), (legacy, json.dumps({'company-info-企业名称': '虚构旧版企业'})), (DRAFT, '{malformed-new')]
    for storage_key, raw in cases:
        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        page = context.new_page()
        watch(page, base)
        # One-time seed via same origin. No business data or real credentials are used.
        page.goto(base + '/apps/deepblm.html?internal_test=1', wait_until='networkidle')
        page.evaluate('''({storage_key, raw}) => {
            localStorage.setItem('sibling-app-fixture', 'keep');
            localStorage.setItem('blm-ai-config', JSON.stringify({apiKey: 'legacy-fixture-never-reuse'}));
            localStorage.setItem('da-ai-config', JSON.stringify({apiKey: 'sibling-fixture-never-read'}));
            if (raw !== null) localStorage.setItem(storage_key, raw);
        }''', {'storage_key': storage_key, 'raw': raw})
        page.reload(wait_until='networkidle')
        expect(page.locator('#workspace')).to_be_visible()
        page.locator('#open-ai-settings').click()
        assert page.locator('#ai-key').input_value() == ''
        expect(page.locator('#legacy-settings')).to_be_visible()
        page.locator('#close-ai-settings').click()
        if raw in ('', '{broken', '{malformed-new'):
            expect(page.locator('#storage-recovery')).to_be_visible()
            write_editor(page, 'company-info-主营业务', '内存恢复草稿')
            assert current_draft(page) == (raw if storage_key == DRAFT else None)
            assert page.evaluate('(k) => localStorage.getItem(k)', storage_key) == raw
            recovery = exported(page, '#export-recovery', directory)
            assert json.loads(recovery.read_text())[storage_key] == raw
            assert 'legacy-fixture-never-reuse' not in recovery.read_text()
        elif raw:
            assert field_value(page, 'company-info-企业名称') == '虚构旧版企业'
        else:
            write_editor(page, 'company-info-主营业务', '新草稿可保存')
            assert '新草稿可保存' in current_draft(page)
        before = page.evaluate('JSON.stringify(localStorage)')
        page.once('dialog', lambda dialog: dialog.dismiss())
        activate(page, '#clear-local')
        assert page.evaluate('JSON.stringify(localStorage)') == before
        page.locator('#open-ai-settings').click()
        page.once('dialog', lambda dialog: dialog.accept())
        page.locator('#clear-legacy-settings').click()
        assert page.evaluate('localStorage.getItem("blm-ai-config")') is None
        assert page.evaluate('localStorage.getItem("da-ai-config")') is not None
        page.locator('#close-ai-settings').click()
        page.once('dialog', lambda dialog: dialog.accept())
        activate(page, '#clear-local')
        assert current_draft(page) is None
        assert page.evaluate('localStorage.getItem("blm-strategy-data")') is None
        assert page.evaluate('localStorage.getItem("sibling-app-fixture")') == 'keep'
        assert page.evaluate('localStorage.getItem("da-ai-config")') is not None
        context.close()

    # A browser that denies localStorage still supports manual editing and JSON download.
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    context.add_init_script("Object.defineProperty(window, 'localStorage', {get() { throw new DOMException('fixture-only storage denied', 'SecurityError'); }});")
    page = context.new_page()
    requests, errors, assets = watch(page, base)
    page.goto(base + '/apps/deepblm.html?internal_test=1', wait_until='networkidle')
    expect(page.locator('#workspace')).to_be_visible()
    expect(page.locator('#storage-recovery')).to_be_visible()
    write_editor(page, 'company-info-主营业务', '虚构无存储草稿')
    path = exported(page, '#export-json', directory)
    assert '虚构无存储草稿' in path.read_text()
    assert not errors and not assets, (errors, assets)
    context.close()


def check_review_sessions(browser, base, directory):
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    requests, errors, assets = watch(page, base)
    page.goto(base + '/apps/deepblm.html?internal_test=1', wait_until='networkidle')
    page.locator('[data-step="strategy-validation"]').click()
    activate(page, '#basic-validation')
    baseline = page.locator('[data-missing-field]').count()
    incoming = Path(directory) / 'review-session-import.json'
    incoming.write_text(json.dumps({f'company-info-{name}': '虚构导入值' for name in
                                   ('企业名称', '主营业务', '行业描述', '企业规模', '企业现状')}, ensure_ascii=False))
    # Import in a report must discard the previous draft's resolved-entry snapshot.
    page.once('dialog', lambda dialog: dialog.accept())
    chooser_import(page, incoming)
    expect(page.locator('#tool-message')).to_contain_text('导入成功')
    expect(page.locator('[data-missing-field]')).to_have_count(baseline - 5)
    expect(page.locator('[data-missing-field^="company-info-"]')).to_have_count(0)
    # A rejected import preserves the active review; successful replacement ends it.
    page.locator('[data-missing-field="gap-机会差距"]').get_by_role('button', name='去补充').click()
    page.once('dialog', lambda dialog: dialog.dismiss())
    chooser_import(page, incoming)
    expect(page.locator('#return-report')).to_be_visible()
    page.once('dialog', lambda dialog: dialog.accept())
    chooser_import(page, incoming)
    expect(page.locator('#tool-message')).to_contain_text('导入成功')
    expect(page.locator('#return-report')).to_have_count(0)
    expect(page.locator('#return-report-footer')).to_have_count(0)
    page.locator('[data-step="strategy-validation"]').click()
    page.locator('[data-missing-field="gap-机会差距"]').get_by_role('button', name='去补充').click()
    write_editor(page, 'gap-机会差距', '虚构会话补充')
    page.locator('#return-report').click()
    expect(page.locator('[data-missing-field="gap-机会差距"]')).to_have_attribute('data-resolved', 'true')
    # Reset starts a fresh review, without resolved entries from before reset.
    page.once('dialog', lambda dialog: dialog.accept())
    activate(page, '#reset-step')
    expect(page.locator('[data-missing-field="gap-机会差距"]')).to_have_count(0)
    expect(page.locator('[data-missing-field]')).to_have_count(baseline - 6)
    page.locator('[data-missing-field="gap-业绩差距"]').get_by_role('button', name='去补充').click()
    page.once('dialog', lambda dialog: dialog.accept())
    activate(page, '#reset-step')
    expect(page.locator('#return-report')).to_have_count(0)
    expect(page.locator('#return-report-footer')).to_have_count(0)
    page.locator('[data-step="strategy-validation"]').click()
    expect(page.locator('[data-missing-field]')).to_have_count(baseline - 5)
    assert not errors and not assets, (errors, assets)
    page.close()


def check_save_failure(browser, base, directory):
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    requests, errors, assets = watch(page, base)
    page.goto(base + '/apps/deepblm.html?internal_test=1', wait_until='networkidle')
    write_editor(page, 'company-info-企业名称', '已保存验收值')
    saved = current_draft(page)
    page.evaluate("""() => {
        const original = Storage.prototype.setItem;
        Storage.prototype.setItem = function(key, value) {
            if (key === 'deepblm-draft-v1') throw new DOMException('fixture-only full', 'QuotaExceededError');
            return original.call(this, key, value);
        };
    }""")
    write_editor(page, 'company-info-主营业务', '虚构内存值仍可导出')
    expect(page.locator('#save-status')).to_contain_text('保存失败')
    assert current_draft(page) == saved
    page.locator('#save-later').click()
    expect(page.locator('#save-status')).to_contain_text('保存失败')
    expect(page.locator('#tool-message')).to_contain_text('仍在内存')
    export_path = exported(page, '#export-json', directory)
    assert '虚构内存值仍可导出' in export_path.read_text()
    incoming = Path(directory) / 'quota-import.json'
    incoming.write_text(json.dumps({'company-info-企业名称': '不能替换原件'}))
    page.once('dialog', lambda dialog: dialog.accept())
    chooser_import(page, incoming)
    expect(page.locator('#tool-message')).to_contain_text('导入失败')
    assert current_draft(page) == saved
    assert field_value(page, 'company-info-企业名称') == '已保存验收值'
    assert field_value(page, 'company-info-主营业务') == '虚构内存值仍可导出'
    assert not errors and not assets, (errors, assets)
    page.close()


if __name__ == '__main__':
    if shared.CHROME_PATH is not None and not Path(shared.CHROME_PATH).is_file():
        raise FileNotFoundError(f'CHROME_PATH is not a file: {shared.CHROME_PATH!r}')
    with shared.site_url() as base, TemporaryDirectory(prefix='deepblm-fixtures-') as directory:
        print(f'Testing Deep BLM at {base}; AI is fixture-only', flush=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=shared.CHROME_PATH, headless=True)
            try:
                check_mobile(browser, base)
                print('PASS: 320/390/820 companion, no heavy vendor/Key/AI, native no-JS entry', flush=True)
                check_desktop(browser, base, directory)
                print('PASS: 15 steps, real editor/save/table/history, downloads/reimport, XSS, explicit fixture AI, 1024/1440', flush=True)
                check_review_sessions(browser, base, directory)
                print('PASS: import/reset start a fresh review; cancelled import preserves active review', flush=True)
                check_save_failure(browser, base, directory)
                print('PASS: quota failure stays truthful, memory export survives, failed import is atomic', flush=True)
                check_writing_composer(browser, base, directory)
                check_composer_draft_boundaries(browser, base, directory)
                print('PASS: composer resets on successful import/scoped reset, cancelled/invalid import preserves input, 95k source sent once and snapshot keyboard scroll', flush=True)
                print('PASS: direct composer, snapshots/targets, shortcuts, keyboard/IME, memory-only requirements, critique/discussion, cancellation/stale rejection and confirmed table apply/undo', flush=True)
                check_global_ai(browser, base, directory)
                print('PASS: global config across 15 steps, opt-in persistence/reload, consent, destination invalidation, dialogs and scoped forget', flush=True)
                check_credential_storage_failures(browser, base, directory)
                print('PASS: strict/malicious credential records, recovery isolation, truthful denied/quota/delete failures', flush=True)
                check_storage(browser, base, directory)
                print('PASS: fresh/legacy/malformed storage, recovery, legacy secrets ignored, explicit scoped cleanup', flush=True)
            finally:
                browser.close()
