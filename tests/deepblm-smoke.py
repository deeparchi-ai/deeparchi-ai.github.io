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
    field(page, field_id).locator('.CodeMirror').evaluate('(node, value) => node.CodeMirror.setValue(value)', value)


def current_draft(page):
    return page.evaluate('(key) => localStorage.getItem(key)', DRAFT)


def exported(page, selector, directory):
    with page.expect_download() as event:
        page.locator(selector).click()
    download = event.value
    target = Path(directory) / download.suggested_filename
    download.save_as(target)
    return target


def chooser_import(page, path):
    with page.expect_file_chooser() as event:
        page.locator('#import-json').click()
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
        assert not any('/vendor/' in u or 'deepblm-workspace' in u or 'deepblm-data' in u or 'signals.mjs' in u or 'analytics-config' in u for u in requests), requests
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
    assert page.locator('.CodeMirror').count() == 5
    assert page.locator('.brand-logo').evaluate('e => e.complete && getComputedStyle(e).height === "88px" && getComputedStyle(e).objectFit === "contain"')
    assert page.locator('link[rel="icon"]').get_attribute('href') == '../assets/deeparchi-favicon.png'
    assert not any('signals.mjs' in u or 'analytics-config' in u for u in requests)
    # First edit uses real browser typing into CodeMirror's focused input.
    company = field(page, 'company-info-企业名称').locator('.CodeMirror')
    company.click()
    page.keyboard.insert_text('虚构验收企业')
    page.wait_for_function('(k) => localStorage.getItem(k)?.includes("虚构验收企业")', arg=DRAFT)
    write_editor(page, 'company-info-企业名称', '甲' * 40)
    write_editor(page, 'company-info-企业名称', '乙' * 41)
    assert field(page, 'company-info-企业名称').locator('.CodeMirror').evaluate('n => n.CodeMirror.getValue()') == '甲' * 40
    write_editor(page, 'company-info-企业名称', '虚构验收企业')
    write_editor(page, 'company-info-主营业务', XSS)
    safe_preview(page)
    saved = current_draft(page)
    page.reload(wait_until='networkidle')
    expect(page.locator('#workspace')).to_be_visible()
    assert '虚构验收企业' in field(page, 'company-info-企业名称').inner_text()
    assert current_draft(page) == saved
    # Every real step renders, including both report and revision editing.
    for nav in page.locator('#step-nav button').all():
        nav.click()
        assert nav.get_attribute('aria-current') == 'step'
        expect(page.locator('#step-heading')).to_be_visible()
        no_overflow(page)
    page.locator('[data-step="gap"]').click()
    table = field(page, 'gap-业绩差距')
    table.locator('textarea[data-row="0"][data-column="0"]').fill('虚构指标类别')
    table.locator('textarea[data-row="0"][data-column="1"]').fill(XSS)
    table.locator('[data-add-row]').click()
    assert field(page, 'gap-业绩差距').locator('tbody tr').count() == 2
    field(page, 'gap-业绩差距').locator('textarea[data-row="1"][data-column="4"]').fill('虚构第二行差距')
    page.locator('#undo').click()
    assert field(page, 'gap-业绩差距').locator('textarea[data-row="1"][data-column="4"]').input_value() == ''
    page.locator('#redo').click()
    assert field(page, 'gap-业绩差距').locator('textarea[data-row="1"][data-column="4"]').input_value() == '虚构第二行差距'
    page.locator('[data-step="strategy-validation"]').click()
    page.locator('#basic-validation').click()
    assert '本地完整性检查' in field(page, 'strategy-validation-逻辑校验报告').inner_text()
    write_editor(page, 'strategy-validation-逻辑校验报告', XSS + '\n## 虚构修订建议\n- 补充市场依据')
    page.locator('[data-step="revision"]').click()
    page.locator('#revision-from-report').click()
    assert '虚构修订建议' in field(page, 'revision-修改建议列表').inner_text()
    safe_preview(page)
    # Explicit non-real fixture AI; no provider is contacted.
    page.locator('[data-step="strategy-validation"]').click()
    field(page, 'strategy-validation-逻辑校验报告').locator('[data-ai-field]').click()
    page.locator('#ai-provider').select_option('custom')
    page.locator('#ai-endpoint').fill(ENDPOINT_FIXTURE)
    page.locator('#ai-model').fill('fixture-model-not-live')
    page.locator('#ai-key').fill(KEY_FIXTURE)
    page.locator('#save-ai-preferences').click()
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
    page.locator('#ai-consent').check()
    page.locator('#ai-send').click()
    expect(page.locator('#ai-apply')).to_be_visible()
    assert len(calls) == 1
    assert KEY_FIXTURE not in page.locator('#ai-result').inner_text()
    safe_preview(page)
    page.once('dialog', lambda dialog: dialog.accept())
    page.locator('#ai-apply').click()
    assert '虚构 AI 校验结果' in field(page, 'strategy-validation-逻辑校验报告').inner_text()
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
        assert '虚构验收企业' in field(page, 'company-info-企业名称').inner_text()
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
        expect(field(page, 'company-info-主营业务').locator('.CodeMirror')).to_be_visible()
        no_overflow(page); screenshot(page, f'workspace-{width}.png')
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
    assert page.locator('#ai-key').input_value() == ''
    assert not page.locator('#ai-consent').is_checked()
    assert page.locator('#ai-endpoint').input_value() == ENDPOINT_FIXTURE
    assert sum(u == ENDPOINT_FIXTURE for u in requests) == ai_requests_before_reload
    assert all(urlsplit(u).netloc == urlsplit(base).netloc or u == ENDPOINT_FIXTURE for u in requests), requests
    assert not errors and not assets, (errors, assets)
    page.close()


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
        page.locator('#open-ai').click()
        assert page.locator('#ai-key').input_value() == ''
        expect(page.locator('#legacy-settings')).to_be_visible()
        if raw in ('', '{broken', '{malformed-new'):
            expect(page.locator('#storage-recovery')).to_be_visible()
            write_editor(page, 'company-info-主营业务', '内存恢复草稿')
            assert current_draft(page) == (raw if storage_key == DRAFT else None)
            assert page.evaluate('(k) => localStorage.getItem(k)', storage_key) == raw
            recovery = exported(page, '#export-recovery', directory)
            assert json.loads(recovery.read_text())[storage_key] == raw
            assert 'legacy-fixture-never-reuse' not in recovery.read_text()
        elif raw:
            assert '虚构旧版企业' in field(page, 'company-info-企业名称').inner_text()
        else:
            write_editor(page, 'company-info-主营业务', '新草稿可保存')
            assert '新草稿可保存' in current_draft(page)
        before = page.evaluate('JSON.stringify(localStorage)')
        page.once('dialog', lambda dialog: dialog.dismiss())
        page.locator('#clear-local').click()
        assert page.evaluate('JSON.stringify(localStorage)') == before
        page.once('dialog', lambda dialog: dialog.accept())
        page.locator('#clear-legacy-settings').click()
        assert page.evaluate('localStorage.getItem("blm-ai-config")') is None
        assert page.evaluate('localStorage.getItem("da-ai-config")') is not None
        page.once('dialog', lambda dialog: dialog.accept())
        page.locator('#clear-local').click()
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
                check_storage(browser, base, directory)
                print('PASS: fresh/legacy/malformed storage, recovery, memory-only Key, explicit scoped cleanup', flush=True)
            finally:
                browser.close()
