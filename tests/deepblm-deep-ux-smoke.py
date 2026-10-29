"""DeepBLM deep-UX acceptance: navigation memory, review/edit/compare, session safety.

All AI traffic is an explicit local fixture (fake endpoint and fake Key); every other
off-origin request is aborted. No real credential or paid provider is ever contacted.

Run with the project virtualenv:
    .venv/bin/python tests/deepblm-deep-ux-smoke.py
Optional: BASE_URL, CHROME_PATH, DEEPBLM_SCREENSHOT_DIR.

Exit codes: 0 all checks passed; 2 the fixed DOM contract is not implemented yet
(the missing selectors are listed); any other non-zero value is a real failure.
"""
from pathlib import Path
import importlib.util
import json
import re
import sys
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location('deepblm_base_smoke', HERE / 'deepblm-smoke.py')
smoke = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(smoke)
from playwright.sync_api import sync_playwright, expect  # noqa: E402

shared = smoke.shared
KEY = smoke.KEY_FIXTURE
ENDPOINT = smoke.ENDPOINT_FIXTURE
DRAFT = smoke.DRAFT
CONFIG = 'deepblm-preferences-v1'


class ContractNotReady(RuntimeError):
    pass


# ---------------------------------------------------------------- infrastructure

BASE_CONTRACT = [
    '#field-outline',
    '#next-missing-field',
    '.step-title',
    '#step-nav button[data-step]',
    '#step-content',
    '#ai-footer',
]
AI_CONTRACT = [
    '#ai-draft-editor',
    '[data-ai-view="edit"]',
    '[data-ai-view="preview"]',
    '[data-ai-view="compare"]',
    '#ai-copy',
    '#ai-copy-fallback',
    '#ai-return',
    '#ai-footer',
    '#ai-apply',
    '#ai-send',
    '#ai-question',
    '#ai-target-select',
    '#ai-result',
    '.ai-result-card',
]


def contract_gaps(page, selectors):
    return [selector for selector in selectors if page.locator(selector).count() == 0]


def preflight(browser, base):
    context = browser.new_context(viewport={'width': 1440, 'height': 900})
    page = context.new_page()
    smoke.watch(page, base)
    page.goto(base + '/apps/deepblm.html?internal_test=1', wait_until='networkidle')
    expect(page.locator('#workspace')).to_be_visible(timeout=15000)
    missing = contract_gaps(page, BASE_CONTRACT)
    opener = page.locator('[data-ai-field="company-info-企业名称"]')
    if opener.count():
        opener.click()
        expect(page.locator('#ai-panel')).to_be_visible()
        missing += contract_gaps(page, AI_CONTRACT)
    else:
        missing.append('[data-ai-field]')
    context.close()
    if missing:
        raise ContractNotReady(', '.join(sorted(set(missing))))


def new_page(browser, base, width=1440, height=900, clipboard=True, init_script=None):
    context = browser.new_context(viewport={'width': width, 'height': height})
    if clipboard:
        context.grant_permissions(['clipboard-write'], origin=base)
    page = context.new_page()
    requests, errors, assets = smoke.watch(page, base)
    if init_script:
        page.add_init_script(init_script)
    page.goto(base + '/apps/deepblm.html?internal_test=1', wait_until='networkidle')
    expect(page.locator('#workspace')).to_be_visible(timeout=15000)
    return context, page, requests, errors, assets


def install_fixture(page, calls, reply):
    """Explicit fake Chat Completions endpoint; supports CORS preflight."""
    cors = {
        'access-control-allow-origin': '*',
        'access-control-allow-methods': 'POST, OPTIONS',
        'access-control-allow-headers': 'Content-Type, Authorization',
    }

    def handler(route):
        request = route.request
        if request.method == 'OPTIONS':
            route.fulfill(status=204, headers=cors)
            return
        assert request.headers.get('authorization') == 'Bearer ' + KEY
        calls.append(request)
        route.fulfill(
            status=200, headers=cors, content_type='application/json',
            body=json.dumps({'choices': [{'message': {'content': reply['content']}}]}),
        )

    page.route(ENDPOINT, handler)
    return handler


def open_global(page):
    # Global settings live in the top bar; the modal AI panel must be closed first.
    if page.locator('#ai-settings').is_visible():
        return
    close_panel(page)
    page.locator('#open-ai-settings').click()
    expect(page.locator('#ai-settings')).to_be_visible()


def configure(page):
    open_global(page)
    smoke.configure_global(page)
    page.locator('#close-ai-settings').click()
    expect(page.locator('#ai-settings')).not_to_be_visible()


def set_consent(page, checked):
    open_global(page)
    if checked:
        page.locator('#ai-consent').check()
    else:
        page.locator('#ai-consent').uncheck()
    page.locator('#close-ai-settings').click()


def open_target(page, field_id):
    if page.locator('#ai-panel').is_visible():
        page.locator('#close-ai').click()
        expect(page.locator('#ai-panel')).not_to_be_visible()
    page.locator(f'[data-ai-field="{field_id}"]').click()
    expect(page.locator('#ai-panel')).to_be_visible()
    expect(page.locator('#ai-target-select')).to_have_value(field_id)


def close_panel(page):
    if page.locator('#ai-panel').is_visible():
        page.locator('#close-ai').click()
        expect(page.locator('#ai-panel')).not_to_be_visible()


def generate(page, calls, reply, content):
    reply['content'] = content
    before = len(calls)
    page.locator('#ai-send').click()
    expect(page.locator('.ai-result-card')).to_have_attribute('data-state', 'success', timeout=15000)
    assert len(calls) == before + 1, f'expected exactly one fixture request, got {len(calls) - before}'


def apply_usable(page):
    return page.evaluate("""() => {
        const b = document.querySelector('#ai-apply');
        if (!b) return false;
        return !b.hidden && !b.disabled && b.getBoundingClientRect().height > 0;
    }""")


def assert_not_adoptable(page, calls, field_id, label):
    assert not apply_usable(page), f'{label}: outdated suggestion is still adoptable'
    state = page.locator('.ai-result-card').get_attribute('data-state')
    if state == 'success':
        text = page.locator('.ai-result-card').inner_text()
        assert re.search('过期|失效|已变化|重新生成|不可采用', text), f'{label}: success shown without an outdated notice'
    before = len(calls)
    page.locator('#ai-target-select').select_option('discussion')
    assert not apply_usable(page), f'{label}: switching to discussion re-enabled adopted output'
    page.locator('#ai-target-select').select_option(field_id)
    assert not apply_usable(page), f'{label}: switching back silently re-enabled the old result'
    assert len(calls) == before, f'{label}: navigation caused an unwanted AI request'


def active_field(page):
    return page.evaluate("""() => {
        const a = document.activeElement;
        const box = a && a.closest ? a.closest('[data-field]') : null;
        return box ? box.dataset.field : null;
    }""")


def active_control(page):
    return page.evaluate("""() => {
        const a = document.activeElement;
        return {
            id: a ? a.id : '',
            tag: a ? a.tagName : '',
            inField: !!(a && a.closest && a.closest('[data-field]')),
            field: a && a.closest && a.closest('[data-field]') ? a.closest('[data-field]').dataset.field : null,
            real: !!(a && (a.matches('input,textarea,select') || a.closest('.CodeMirror'))),
        };
    }""")


def flat_draft(page):
    raw = page.evaluate('(key) => localStorage.getItem(key)', DRAFT)
    if raw is None:
        return {}
    document = json.loads(raw)
    return {f"{step['id']}-{name}": value for step in document['steps'] for name, value in step['data'].items()}


def scroll_top(page, selector='#step-content'):
    return page.locator(selector).evaluate('n => n.scrollTop')


def scroll_to(page, selector, value):
    page.locator(selector).evaluate('(n, v) => { n.scrollTop = v; }', value)


def step_button(page, step_id):
    return page.locator(f'#step-nav [data-step="{step_id}"]')


def outline_row(page, field_id):
    marker = page.locator(f'#field-outline [data-outline-field="{field_id}"]')
    return marker.locator('xpath=ancestor-or-self::li[1]')


def outline_jump(page, field_id):
    row = outline_row(page, field_id)
    inner = row.locator('button')
    if inner.count():
        inner.first.click()
    else:
        page.locator(f'#field-outline [data-outline-field="{field_id}"]').click()


def wait_active_field(page, field_id):
    page.wait_for_function("""id => {
        const a = document.activeElement;
        const box = a && a.closest ? a.closest('[data-field]') : null;
        return !!box && box.dataset.field === id;
    }""", arg=field_id)


def current_step_id(page):
    return page.evaluate("""() => {
        const b = document.querySelector('#step-nav [aria-current="step"]');
        return b ? b.dataset.step : null;
    }""")


def screenshot(page, name):
    smoke.screenshot(page, name)


def assert_clean(errors, assets):
    assert not errors, errors
    assert not assets, assets


# ---------------------------------------------------------------- A. navigation

def fill_company(page):
    values = {
        '企业名称': '虚构导航验收企业',
        '主营业务': '虚构设备监测服务',
        '行业描述': '虚构工业服务行业',
        '企业规模': '虚构八十人规模',
        '企业现状': '虚构成长阶段，续费数据待核实',
    }
    for name, value in values.items():
        smoke.write_editor(page, f'company-info-{name}', value)


def check_navigation(browser, base):
    context, page, requests, errors, assets = new_page(browser, base)
    try:
        assert page.locator('#step-heading').inner_text() == '企业信息'
        titles = page.locator('.step-title')
        assert titles.count() >= 1, 'the step title must carry a stable .step-title label'
        assert any('企业信息' in text for text in titles.all_inner_texts())
        assert page.locator('#step-nav button[data-step]').count() == 15

        # Actual per-step completion, derived only from nonblank values.
        nav = step_button(page, 'company-info')
        assert '企业信息' in nav.inner_text()
        assert '未开始' in nav.inner_text() and re.search(r'0\s*/\s*5', nav.inner_text()), nav.inner_text()
        assert re.search(r'0\s*/\s*15', page.locator('#progress-label').inner_text())
        assert page.locator('#field-outline [data-outline-field]').count() == 5
        expect(outline_row(page, 'company-info-企业名称')).to_contain_text('待补充')
        assert '%' not in page.locator('#current-completion').inner_text()
        assert re.search(r'0\s*/\s*5', page.locator('#current-completion').inner_text())

        # Outline jump focuses the real control, not a proxy.
        outline_jump(page, 'company-info-企业名称')
        expect(page.locator('#company-info-企业名称')).to_be_focused()
        assert page.locator('#company-info-企业名称').evaluate('n => n.tagName') == 'INPUT'

        page.locator('#company-info-企业名称').type('虚构导航验收企业')
        assert '填写中' in nav.inner_text() and re.search(r'1\s*/\s*5', nav.inner_text()), nav.inner_text()
        expect(outline_row(page, 'company-info-企业名称')).to_contain_text('已填写')
        assert re.search(r'1\s*/\s*5', page.locator('#current-completion').inner_text())

        # One "next missing" action focuses an actually blank, real control.
        assert page.locator('#next-missing-field').is_enabled()
        page.locator('#next-missing-field').click()
        page.wait_for_function("""() => {
            const a = document.activeElement;
            return !!a && (!!a.closest('.CodeMirror') || a.matches('input,textarea'));
        }""")
        control = active_control(page)
        assert control['real'] and control['field'] and control['field'].startswith('company-info-'), control
        assert control['field'] != 'company-info-企业名称', 'next-missing must not repeat the field being edited'
        assert smoke.field_value(page, control['field']).strip() == '', control

        # First entry into a long step starts at the top.
        step_button(page, 'business-design').click()
        assert current_step_id(page) == 'business-design'
        assert page.locator('#step-heading').inner_text() == '业务设计'
        assert page.locator('#step-content').evaluate('n => n.scrollHeight > n.clientHeight')
        assert scroll_top(page) == 0, 'first entry must start at the top'
        expect(page.locator('#step-heading')).to_be_focused()

        # Fill, focus a distant field, scroll, leave and come back.
        for name in ('客户选择', '价值主张', '价值获取'):
            smoke.write_editor(page, f'business-design-{name}', '虚构内容：' + name)
        risk = page.locator('[data-field="business-design-风险管理"] .CodeMirror')
        risk.click()
        page.keyboard.type('虚构上次编辑位置')
        target_scroll = min(160, page.locator('#step-content').evaluate('n => n.scrollHeight - n.clientHeight'))
        scroll_to(page, '#step-content', target_scroll)
        assert scroll_top(page) == target_scroll
        assert active_field(page) == 'business-design-风险管理'

        step_button(page, 'gap').click()
        step_button(page, 'business-design').click()
        assert current_step_id(page) == 'business-design'
        delta = abs(scroll_top(page) - target_scroll)
        assert delta <= 2, f'scroll memory lost: {scroll_top(page)} vs {target_scroll}'
        assert active_field(page) == 'business-design-风险管理', active_control(page)
        assert active_control(page)['real']

        # Completion reacts to clearing and undo, not to business wording.
        step_button(page, 'company-info').click()
        fill_company(page)
        assert '已填写' in nav.inner_text() and re.search(r'5\s*/\s*5', nav.inner_text()), nav.inner_text()
        assert page.locator('#next-missing-field').is_disabled()
        assert re.search(r'2\s*/\s*15', page.locator('#progress-label').inner_text())
        name = page.locator('#company-info-企业名称')
        name.click()
        name.press('Control+a')
        name.press('Backspace')
        assert '填写中' in nav.inner_text() and re.search(r'4\s*/\s*5', nav.inner_text()), nav.inner_text()
        expect(outline_row(page, 'company-info-企业名称')).to_contain_text('待补充')
        assert page.locator('#next-missing-field').is_enabled()
        smoke.activate(page, '#undo')
        expect(name).to_have_value('虚构导航验收企业')
        assert '已填写' in nav.inner_text() and re.search(r'5\s*/\s*5', nav.inner_text())
        smoke.activate(page, '#redo')
        expect(name).to_have_value('')
        assert re.search(r'4\s*/\s*5', nav.inner_text())
        smoke.activate(page, '#undo')
        expect(name).to_have_value('虚构导航验收企业')

        # Table row add/delete keeps focus on a real cell of the same table.
        step_button(page, 'gap').click()
        table = page.locator('[data-field="gap-业绩差距"]')
        rows_before = table.locator('tbody tr').count()
        table.locator('[data-add-row]').click()
        page.wait_for_function("""() => {
            const a = document.activeElement;
            return !!a && a.matches('textarea[data-row]') && !!a.closest('[data-field="gap-业绩差距"]');
        }""")
        rows_after = table.locator('tbody tr').count()
        assert rows_after == rows_before + 1, (rows_before, rows_after)
        assert page.evaluate('document.activeElement.dataset.row') == str(rows_after - 1)
        page.keyboard.type('虚构新增行')
        assert table.locator('tbody tr').last.locator('textarea[data-column="0"]').input_value() == '虚构新增行'
        assert len(flat_draft(page)['gap-业绩差距']) == rows_after
        table.locator('tbody tr').last.get_by_role('button', name=re.compile('删除')).click()
        page.wait_for_function("""() => {
            const a = document.activeElement;
            return !!a && a.matches('textarea[data-row]') && !!a.closest('[data-field="gap-业绩差距"]');
        }""")
        assert table.locator('tbody tr').count() == rows_after - 1
        assert active_field(page) == 'gap-业绩差距', active_control(page)
        assert len(flat_draft(page)['gap-业绩差距']) == rows_after - 1

        # Report jump and return restore both the step and the reviewed row.
        step_button(page, 'strategy-validation').click()
        expect(page.locator('#missing-fields')).to_be_visible()
        row = page.locator('[data-missing-field]').first
        missing_id = row.get_attribute('data-missing-field')
        expected_step = missing_id.rsplit('-', 1)[0]
        saved_scroll = scroll_top(page)
        row.get_by_role('button').click()
        assert current_step_id(page) == expected_step, (current_step_id(page), expected_step)
        expect(page.locator(f'[data-missing-field="{missing_id}"]')).to_have_count(0)
        wait_active_field(page, missing_id)
        page.locator('#return-report').click()
        assert current_step_id(page) == 'strategy-validation'
        assert abs(scroll_top(page) - saved_scroll) <= 2, (scroll_top(page), saved_scroll)
        returned = page.evaluate("""() => {
            const a = document.activeElement;
            const row = a && a.closest ? a.closest('[data-missing-field]') : null;
            return row ? row.dataset.missingField : null;
        }""")
        assert returned == missing_id, returned

        assert_clean(errors, assets)
        screenshot(page, 'deep-ux-navigation.png')
        # Tool-wide clearing must also discard view memories from the previous plan.
        step_button(page, 'company-info').click()
        smoke.write_editor(page, 'company-info-企业现状', '虚构清除前的字段内容')
        page.locator('[data-field="company-info-企业现状"]').scroll_into_view_if_needed()
        assert scroll_top(page) > 0
        step_button(page, 'business-design').click()
        scroll_to(page, '#step-content', 500)
        menu = page.locator('#settings-menu')
        if not menu.evaluate('node => node.open'):
            menu.locator('summary').click()
        page.once('dialog', lambda dialog: dialog.accept())
        page.locator('#clear-local').click()
        assert current_step_id(page) == 'company-info'
        assert scroll_top(page) == 0
        assert flat_draft(page) == {}
        step_button(page, 'business-design').click()
        assert scroll_top(page) == 0
        expect(page.locator('#step-heading')).to_be_focused()
        step_button(page, 'company-info').click()
        assert scroll_top(page) == 0
        expect(page.locator('#step-heading')).to_be_focused()
        assert_clean(errors, assets)
    finally:
        context.close()


# ---------------------------------------------------------------- B. review flow

def check_review_flow(browser, base, directory):
    context, page, requests, errors, assets = new_page(browser, base)
    calls, reply = [], {'content': ''}
    install_fixture(page, calls, reply)
    try:
        configure(page)
        original = '虚构原文：设备监测服务，客户续费数据待核实。'
        smoke.write_editor(page, 'company-info-企业现状', original)
        open_target(page, 'company-info-企业现状')

        assert page.locator('#ai-footer').is_visible(), 'action footer must be present before generation'
        expect(page.locator('#ai-draft-editor')).to_have_count(1)
        assert page.locator('#ai-draft-editor').evaluate('n => n.tagName') == 'TEXTAREA'
        assert page.locator('#ai-copy-fallback').evaluate('n => n.tagName') == 'TEXTAREA'
        assert page.locator('#ai-copy-fallback').get_attribute('readonly') is not None

        page.evaluate("""() => {
            window.__copied = null;
            const clipboard = navigator.clipboard;
            if (!clipboard) return;
            const real = clipboard.writeText.bind(clipboard);
            clipboard.writeText = text => { window.__copied = text; return real(text); };
        }""")

        generate(page, calls, reply, '虚构建议初稿：设备监测服务，客户续费数据待补充。')
        expect(page.locator('#ai-draft-editor')).to_have_value('虚构建议初稿：设备监测服务，客户续费数据待补充。')
        expect(page.locator('[data-ai-view="preview"]')).to_have_attribute('aria-pressed', 'true')
        expect(page.locator('#ai-result')).to_contain_text('虚构建议初稿')

        # Compare shows the actual original source.
        page.locator('[data-ai-view="compare"]').click()
        expect(page.locator('[data-ai-view="compare"]')).to_have_attribute('aria-pressed', 'true')
        expect(page.locator('[data-ai-view="preview"]')).to_have_attribute('aria-pressed', 'false')
        compare_text = page.locator('#ai-original').inner_text()
        assert original in compare_text, compare_text
        assert '虚构建议初稿' not in compare_text, 'compare must show the real source, not the suggestion'
        expect(page.locator('#ai-compare-draft')).to_contain_text('虚构建议初稿')
        expect(page.locator('#ai-original')).to_be_visible()
        expect(page.locator('#ai-compare-draft')).to_be_visible()

        # Editing drives preview and copy.
        page.locator('[data-ai-view="edit"]').click()
        expect(page.locator('[data-ai-view="edit"]')).to_have_attribute('aria-pressed', 'true')
        expect(page.locator('#ai-draft-editor')).to_be_visible()
        edited = '虚构编辑稿：设备服务续费待核实（人工修订）。'
        page.locator('#ai-draft-editor').fill(edited)
        page.locator('[data-ai-view="compare"]').click()
        expect(page.locator('#ai-compare-draft')).to_have_text(edited)
        expect(page.locator('#ai-original')).to_have_text(original)
        page.locator('[data-ai-view="preview"]').click()
        expect(page.locator('#ai-result')).to_contain_text('虚构编辑稿')
        assert '虚构建议初稿' not in page.locator('#ai-result').inner_text()
        smoke.safe_preview(page)
        page.locator('#ai-copy').click()
        page.wait_for_function('() => window.__copied !== null')
        assert page.evaluate('window.__copied') == edited, 'copy must use the latest edited draft'
        expect(page.locator('#ai-message')).to_contain_text('已复制')

        # Same target close/reopen and target round-trip: edited draft, no new request.
        before = len(calls)
        close_panel(page)
        open_target(page, 'company-info-企业现状')
        expect(page.locator('.ai-result-card')).to_have_attribute('data-state', 'success')
        expect(page.locator('#ai-draft-editor')).to_have_value(edited)
        assert len(calls) == before
        page.locator('#ai-target-select').select_option('company-info-企业名称')
        expect(page.locator('.ai-result-card')).to_have_attribute('data-state', 'empty')
        page.locator('#ai-target-select').select_option('company-info-企业现状')
        expect(page.locator('#ai-draft-editor')).to_have_value(edited)
        assert len(calls) == before, 'switching targets must never request'

        # Focus theft: a user typing in the question keeps focus when the reply lands.
        deferred = """endpoint => {
            window.__realFetch = window.fetch;
            window.__pending = [];
            window.fetch = (url, options) => {
                if (!String(url).startsWith(endpoint)) return window.__realFetch(url, options);
                let resolve;
                const promise = new Promise(r => { resolve = r; });
                const entry = {resolve, aborted: false};
                window.__pending.push(entry);
                options.signal.addEventListener('abort', () => { entry.aborted = true; });
                return promise;
            };
        }"""
        page.evaluate(deferred, ENDPOINT)
        page.locator('#ai-send').click()
        expect(page.locator('#ai-cancel')).to_be_enabled()
        page.locator('#ai-question').click()
        page.keyboard.type('虚构等待中继续输入')
        assert page.evaluate('window.__pending.length') == 1
        page.evaluate("""async content => {
            window.__pending.shift().resolve(new Response(
                JSON.stringify({choices: [{message: {content}}]}),
                {status: 200, headers: {'Content-Type': 'application/json'}}));
            await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
        }""", '虚构迟到但被接受的回复')
        expect(page.locator('.ai-result-card')).to_have_attribute('data-state', 'success')
        expect(page.locator('#ai-question')).to_be_focused()
        expect(page.locator('#ai-question')).to_have_value('虚构等待中继续输入')
        page.evaluate('() => { window.fetch = window.__realFetch; }')

        # Adoption is confirmed, writes the edited draft (not the raw reply), and is undoable.
        page.locator('[data-ai-view="edit"]').click()
        final = '虚构采用稿：设备服务续费待核实，由人工确认。'
        page.locator('#ai-draft-editor').fill(final)
        page.once('dialog', lambda dialog: dialog.dismiss())
        page.locator('#ai-apply').click()
        assert smoke.field_value(page, 'company-info-企业现状') == original, 'dismissed confirmation must not write'
        page.once('dialog', lambda dialog: dialog.accept())
        page.locator('#ai-apply').click()
        expect(page.locator('#ai-adopted-status')).to_contain_text('已采用')
        expect(page.locator('#ai-return')).to_be_visible()
        assert smoke.field_value(page, 'company-info-企业现状') == final
        assert flat_draft(page)['company-info-企业现状'] == final
        page.locator('#ai-return').click()
        expect(page.locator('#ai-panel')).not_to_be_visible()
        wait_active_field(page, 'company-info-企业现状')
        smoke.activate(page, '#undo')
        assert smoke.field_value(page, 'company-info-企业现状') == original, 'adoption must be undoable'

        # Adopted result is consumed: reopen never re-offers the old draft.
        open_target(page, 'company-info-企业现状')
        assert not apply_usable(page)
        close_panel(page)

        # Inspect and discussion stay non-applicable even after editing the draft.
        open_target(page, 'company-info-企业现状')
        page.locator('[data-ai-action="inspect"]').click()
        generate(page, calls, reply, '虚构检查清单：缺客户续费数据。')
        page.locator('[data-ai-view="edit"]').click()
        page.locator('#ai-draft-editor').fill('虚构检查稿编辑')
        assert not apply_usable(page), 'inspect result must never be adoptable'
        page.locator('#ai-discussion').click()
        generate(page, calls, reply, '虚构讨论：先补续费口径。')
        page.locator('[data-ai-view="edit"]').click()
        page.locator('#ai-draft-editor').fill('虚构讨论编辑')
        assert not apply_usable(page), 'discussion result must never be adoptable'
        close_panel(page)

        assert_clean(errors, assets)
        screenshot(page, 'deep-ux-review.png')
    finally:
        context.close()


def check_clipboard_fallback(browser, base):
    deny = """Object.defineProperty(navigator, 'clipboard', {
        configurable: true,
        value: {writeText: () => Promise.reject(new DOMException('denied', 'NotAllowedError'))},
    });"""
    context, page, requests, errors, assets = new_page(browser, base, clipboard=False, init_script=deny)
    calls, reply = [], {'content': '虚构建议用于复制回退。'}
    install_fixture(page, calls, reply)
    try:
        configure(page)
        open_target(page, 'company-info-企业名称')
        generate(page, calls, reply, reply['content'])
        edited = '虚构回退编辑稿：只能手工复制。'
        page.locator('[data-ai-view="edit"]').click()
        page.locator('#ai-draft-editor').fill(edited)
        page.locator('#ai-copy').click()
        fallback = page.locator('#ai-copy-fallback')
        expect(fallback).to_be_visible()
        expect(fallback).to_have_value(edited)
        assert fallback.get_attribute('readonly') is not None
        assert fallback.evaluate('n => n.tagName') == 'TEXTAREA'
        expect(fallback).to_be_focused()
        fallback.press('Control+a')
        selected = fallback.evaluate('n => [n.selectionStart, n.selectionEnd, n.value.length]')
        assert selected[0] == 0 and selected[1] == selected[2] == len(edited), selected
        expect(page.locator('#ai-message')).to_contain_text('手动')
        # Failure is truthful even when the legacy manual textarea is present.
        expect(page.locator('#ai-apply')).to_be_visible()
        # A delayed permission result belongs to the clicked target, never its replacement.
        for outcome in ('reject', 'resolve'):
            page.evaluate("""() => {
                Object.defineProperty(navigator, 'clipboard', {configurable:true,
                    value:{writeText:() => new Promise((resolve,reject) => {
                        window.__copySettlers={resolve,reject};
                    })}});
            }""")
            before_requests = len(calls)
            page.locator('#ai-copy').click()
            page.locator('#ai-target-select').select_option('company-info-主营业务')
            focus_before = page.evaluate('document.activeElement.id')
            page.evaluate("""async outcome => {
                if(outcome==='reject') window.__copySettlers.reject(new Error('fixture delayed denial'));
                else window.__copySettlers.resolve();
                await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
            }""", outcome)
            expect(fallback).not_to_be_visible()
            expect(fallback).to_have_value('')
            expect(page.locator('.ai-result-card')).to_have_attribute('data-state', 'empty')
            assert page.evaluate('document.activeElement.id') == focus_before
            assert page.locator('#ai-message').inner_text() == ''
            assert len(calls) == before_requests
            page.locator('#ai-target-select').select_option('company-info-企业名称')
            expect(page.locator('#ai-draft-editor')).to_have_value(edited)
        assert_clean(errors, assets)
    finally:
        context.close()


# ---------------------------------------------------------------- B. tables/adoption

def check_table_safety(browser, base):
    context, page, requests, errors, assets = new_page(browser, base)
    calls, reply = [], {'content': ''}
    install_fixture(page, calls, reply)
    try:
        configure(page)
        step_button(page, 'gap').click()
        open_target(page, 'gap-业绩差距')
        rows = [['虚构指标类别', '虚构指标', '待核实', '待确认', '虚构差距']]
        generate(page, calls, reply, json.dumps(rows, ensure_ascii=False))
        page.locator('[data-ai-view="edit"]').click()
        panel_text = page.locator('#ai-panel').inner_text()
        assert 'JSON' in panel_text, 'editable table draft must explain the JSON shape'
        for column in ('关键指标类别', '指标', '现状', '目标', '差距'):
            assert column in panel_text, column
        page.locator('#ai-draft-editor').fill('[['
                                              '"错误列数"]]')
        before_storage = page.evaluate('(key) => localStorage.getItem(key)', DRAFT)
        before_cells = [n.input_value() for n in page.locator('[data-field="gap-业绩差距"] textarea[data-row]').all()]
        dialogs = []

        def dismiss_dialog(dialog):
            dialogs.append(dialog.message)
            dialog.dismiss()

        page.on('dialog', dismiss_dialog)
        page.locator('#ai-apply').click()
        page.wait_for_timeout(500)
        page.remove_listener('dialog', dismiss_dialog)
        assert not dialogs, f'invalid JSON must be rejected before any confirmation: {dialogs}'
        assert page.evaluate('(key) => localStorage.getItem(key)', DRAFT) == before_storage, 'invalid table edit touched storage'
        after_cells = [n.input_value() for n in page.locator('[data-field="gap-业绩差距"] textarea[data-row]').all()]
        assert after_cells == before_cells
        expect(page.locator('#ai-message')).to_contain_text(re.compile('未改写|不符合|无效|JSON'))

        # A valid edited JSON array applies as a whole, not an append.
        page.locator('#ai-draft-editor').fill(json.dumps(rows, ensure_ascii=False))
        page.locator('[data-ai-view="preview"]').click()
        page.once('dialog', lambda dialog: dialog.accept())
        page.locator('#ai-apply').click()
        expect(page.locator('[data-field="gap-业绩差距"] textarea[data-row="0"][data-column="0"]')).to_have_value(rows[0][0])
        assert flat_draft(page)['gap-业绩差距'] == rows
        expect(page.locator('#ai-adopted-status')).to_contain_text('已采用')
        page.locator('#ai-return').click()
        expect(page.locator('#ai-panel')).not_to_be_visible()
        smoke.activate(page, '#undo')
        assert flat_draft(page)['gap-业绩差距'] != rows, 'table adoption must be undoable'
        assert_clean(errors, assets)
    finally:
        context.close()


# ---------------------------------------------------------------- B/C. layout

def check_layout(browser, base):
    context, page, requests, errors, assets = new_page(browser, base)
    calls, reply = [], {'content': ''}
    install_fixture(page, calls, reply)
    try:
        configure(page)
        long_result = '\n\n'.join(f'虚构建议第 {i} 条：数据待核实，需人工判断。' for i in range(1, 121))
        open_target(page, 'company-info-企业现状')
        generate(page, calls, reply, long_result)
        for width, height in ((1440, 900), (1024, 768), (1440, 560)):
            page.set_viewport_size({'width': width, 'height': height})
            expect(page.locator('#ai-footer')).to_be_visible()
            footer = page.locator('#ai-footer').bounding_box()
            assert footer['y'] >= -1 and footer['y'] + footer['height'] <= height + 1, (width, height, footer)
            assert page.locator('#ai-footer #ai-apply').count() == 1
            assert page.locator('#ai-footer #ai-copy').count() == 1
            assert page.locator('#ai-footer #ai-return').count() == 1
            assert page.locator('#ai-footer #ai-copy').is_visible()
            assert page.locator('#ai-footer #ai-return').is_visible()
            assert page.locator('.ai-scroll').evaluate('n => n.scrollHeight > n.clientHeight'), 'long result must scroll inside the dialog'
            page.locator('.ai-scroll').evaluate('n => { n.scrollTop = n.scrollHeight; }')
            page.wait_for_timeout(100)
            footer = page.locator('#ai-footer').bounding_box()
            assert footer['y'] + footer['height'] <= height + 1, f'footer buried at {width}x{height}: {footer}'
            assert footer['y'] >= 0
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), f'horizontal overflow at {width}'
            panel = page.locator('#ai-panel').bounding_box()
            assert panel['x'] >= -1 and panel['x'] + panel['width'] <= width + 1
            assert panel['y'] >= -1 and panel['y'] + panel['height'] <= height + 1
            screenshot(page, f'deep-ux-footer-{width}x{height}.png')
        page.locator('#close-ai').click()
        assert_clean(errors, assets)
    finally:
        context.close()


# ---------------------------------------------------------------- C. session safety

def check_session_safety(browser, base, directory):
    context, page, requests, errors, assets = new_page(browser, base)
    calls, reply = [], {'content': ''}
    install_fixture(page, calls, reply)
    import_file = Path(directory) / 'deep-ux-import.json'
    import_file.write_text(json.dumps({'company-info-企业名称': '虚构导入企业'}, ensure_ascii=False))
    invalid_file = Path(directory) / 'deep-ux-invalid.json'
    invalid_file.write_text('{invalid')
    try:
        configure(page)
        field_id = 'company-info-企业名称'
        generate_text = '虚构会话建议：企业名称合规待核验。'

        def fresh_result():
            open_target(page, field_id)
            generate(page, calls, reply, generate_text)
            assert apply_usable(page), 'fresh result should be adoptable'

        # (1) any manual field change makes the old result unusable.
        fresh_result()
        close_panel(page)
        smoke.write_editor(page, 'company-info-主营业务', '虚构手工编辑导致上下文变化')
        open_target(page, field_id)
        assert_not_adoptable(page, calls, field_id, 'manual field edit')

        # (2) undo/redo also invalidates.
        close_panel(page)
        page.locator(f'#{field_id}').fill('虚构可撤销名称')
        fresh_result()
        close_panel(page)
        smoke.activate(page, '#undo')
        open_target(page, field_id)
        assert_not_adoptable(page, calls, field_id, 'undo')

        # (3) connection/config change.
        fresh_result()
        open_global(page)
        page.locator('#ai-model').fill('fixture-model-changed')
        page.locator('#save-ai-preferences').click()
        page.locator('#close-ai-settings').click()
        open_target(page, field_id)
        assert_not_adoptable(page, calls, field_id, 'config change')
        close_panel(page)
        configure(page)

        # (4) consent change.
        fresh_result()
        set_consent(page, False)
        open_target(page, field_id)
        assert_not_adoptable(page, calls, field_id, 'consent withdrawn')
        set_consent(page, True)
        close_panel(page)

        # (5) another tab touching global AI storage.
        fresh_result()
        other = context.new_page()
        smoke.watch(other, base)
        other.goto(base + '/apps/deepblm.html?internal_test=1', wait_until='networkidle')
        other.evaluate("""([key, config]) => localStorage.setItem(key, JSON.stringify(config))""",
                       [CONFIG, {'provider': 'custom', 'endpoint': ENDPOINT, 'model': 'other-tab-model'}])
        expect(page.locator('#ai-panel')).to_be_visible()
        assert_not_adoptable(page, calls, field_id, 'other tab config')
        other.close()
        close_panel(page)
        configure(page)

        # (6) cancelled reset preserves; confirmed reset clears only that step.
        fresh_result()
        close_panel(page)
        step_button(page, 'gap').click()
        page.locator('#open-ai').click()
        page.locator('#ai-discussion').click()
        page.locator('#ai-question').fill('虚构其他步骤讨论，不应被本步重置清除')
        close_panel(page)
        step_button(page, 'company-info').click()
        page.once('dialog', lambda dialog: dialog.dismiss())
        smoke.activate(page, '#reset-step')
        open_target(page, field_id)
        expect(page.locator('.ai-result-card')).to_have_attribute('data-state', 'success')
        assert apply_usable(page), 'cancelled reset must preserve the working result'
        close_panel(page)
        page.once('dialog', lambda dialog: dialog.accept())
        smoke.activate(page, '#reset-step')
        open_target(page, field_id)
        assert_not_adoptable(page, calls, field_id, 'confirmed reset')
        close_panel(page)
        step_button(page, 'gap').click()
        page.locator('#open-ai').click()
        page.locator('#ai-discussion').click()
        expect(page.locator('#ai-question')).to_have_value('虚构其他步骤讨论，不应被本步重置清除')
        close_panel(page)
        step_button(page, 'company-info').click()

        # (7) cancelled / invalid / quota-failed imports preserve the session.
        # Cancelled import: the user declines the replace confirmation.
        fresh_result()
        close_panel(page)
        page.once('dialog', lambda dialog: dialog.dismiss())
        smoke.chooser_import(page, import_file)
        open_target(page, field_id)
        expect(page.locator('.ai-result-card')).to_have_attribute('data-state', 'success')
        assert apply_usable(page), 'cancelled import must preserve the working session'
        close_panel(page)

        # Invalid import: rejected before any confirmation, draft/storage untouched.
        fresh_result()
        close_panel(page)
        before = page.evaluate('(key) => localStorage.getItem(key)', DRAFT)
        smoke.chooser_import(page, invalid_file)
        expect(page.locator('#tool-message')).to_contain_text('导入失败')
        assert page.evaluate('(key) => localStorage.getItem(key)', DRAFT) == before
        open_target(page, field_id)
        expect(page.locator('.ai-result-card')).to_have_attribute('data-state', 'success')
        assert apply_usable(page), 'invalid import must preserve the working session'
        close_panel(page)

        # Quota-failed import: storage rejects the write after the user confirms.
        fresh_result()
        close_panel(page)
        page.evaluate("""() => {
            window.__originalSetItem = Storage.prototype.setItem;
            Storage.prototype.setItem = function (key, value) {
                if (key === 'deepblm-draft-v1') throw new DOMException('quota', 'QuotaExceededError');
                return window.__originalSetItem.call(this, key, value);
            };
        }""")
        before = page.evaluate('(key) => localStorage.getItem(key)', DRAFT)
        page.once('dialog', lambda dialog: dialog.accept())
        smoke.chooser_import(page, import_file)
        expect(page.locator('#tool-message')).to_contain_text('导入失败')
        page.evaluate('() => { Storage.prototype.setItem = window.__originalSetItem; }')
        assert page.evaluate('(key) => localStorage.getItem(key)', DRAFT) == before
        open_target(page, field_id)
        expect(page.locator('.ai-result-card')).to_have_attribute('data-state', 'success')
        assert apply_usable(page), 'quota-failed import must preserve the working session'
        close_panel(page)

        # (8) cancel / late reply can never be revived as success.
        open_target(page, field_id)
        page.evaluate("""endpoint => {
            window.__realFetch = window.fetch;
            window.__late = [];
            window.fetch = (url, options) => {
                if (!String(url).startsWith(endpoint)) return window.__realFetch(url, options);
                let resolve;
                const promise = new Promise(r => { resolve = r; });
                const entry = {resolve, aborted: false};
                window.__late.push(entry);
                options.signal.addEventListener('abort', () => { entry.aborted = true; });
                return promise;
            };
        }""", ENDPOINT)
        page.locator('#ai-send').click()
        expect(page.locator('#ai-cancel')).to_be_enabled()
        page.keyboard.press('Escape')
        expect(page.locator('#ai-panel')).not_to_be_visible()
        assert page.evaluate('window.__late[0].aborted') is True
        page.evaluate("""async content => {
            window.__late[0].resolve(new Response(
                JSON.stringify({choices: [{message: {content}}]}),
                {status: 200, headers: {'Content-Type': 'application/json'}}));
            await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
        }""", '虚构迟到回复不得复活')
        page.evaluate('() => { window.fetch = window.__realFetch; }')
        open_target(page, field_id)
        expect(page.locator('#ai-result')).not_to_contain_text('虚构迟到回复不得复活')
        assert not apply_usable(page), 'a cancelled/late reply must never become applicable'
        close_panel(page)

        # (9) successful import clears every working session, including discussion.
        fresh_result()
        page.locator('#ai-question').fill('虚构将被导入清除的要求')
        close_panel(page)
        page.once('dialog', lambda dialog: dialog.accept())
        smoke.chooser_import(page, import_file)
        expect(page.locator('#tool-message')).to_have_text('导入成功。')
        open_target(page, field_id)
        expect(page.locator('#ai-question')).to_have_value('')
        assert not apply_usable(page)
        page.locator('#ai-discussion').click()
        expect(page.locator('#ai-question')).to_have_value('')
        close_panel(page)

        assert_clean(errors, assets)
        screenshot(page, 'deep-ux-sessions.png')
    finally:
        context.close()


# ---------------------------------------------------------------- main

def main():
    if shared.CHROME_PATH is not None and not Path(shared.CHROME_PATH).is_file():
        raise FileNotFoundError(f'CHROME_PATH is not a file: {shared.CHROME_PATH!r}')
    with shared.site_url() as base, TemporaryDirectory(prefix='deepblm-deep-ux-') as directory:
        print(f'Testing DeepBLM deep UX at {base}; AI is fixture-only', flush=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=shared.CHROME_PATH, headless=True)
            try:
                try:
                    preflight(browser, base)
                except ContractNotReady as error:
                    print('BLOCKED: fixed DOM contract not implemented yet — missing: ' + str(error), flush=True)
                    return 2
                print('PASS: DOM contract present (outline, next-missing, step-title, AI footer/editor/views/copy/return)', flush=True)
                check_navigation(browser, base)
                print('PASS: step indicators from real values; outline/next-missing; long-form scroll+focus memory; table add/delete focus; report jump/return', flush=True)
                check_review_flow(browser, base, directory)
                print('PASS: generated→edited→preview/compare→copy→confirmed adopt/undo; no focus theft; same-target restore without requests; inspect/discussion not adoptable', flush=True)
                check_clipboard_fallback(browser, base)
                print('PASS: truthful copy success and readonly keyboard-selectable fallback when clipboard is denied', flush=True)
                check_table_safety(browser, base)
                print('PASS: table JSON guidance, malformed edit mutates nothing, valid edit replaces atomically and is undoable', flush=True)
                check_layout(browser, base)
                print('PASS: long result keeps sticky footer actions visible at 1440x900, 1024x768 and 1440x560', flush=True)
                check_session_safety(browser, base, directory)
                print('PASS: stale results never re-adoptable after edit/undo/config/consent/other-tab/reset/import; cancelled or late replies never revived; failed imports keep sessions', flush=True)
            finally:
                browser.close()
    print('PASS: DeepBLM deep UX acceptance complete', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
