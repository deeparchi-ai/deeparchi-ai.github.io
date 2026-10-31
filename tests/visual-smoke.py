from pathlib import Path
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from threading import Thread
from urllib.parse import parse_qs, urlsplit

try:
    from playwright.sync_api import sync_playwright
except ImportError as error:
    raise SystemExit(
        "Playwright is required: install requirements-dev.txt in a virtual environment, "
        "then run python -m playwright install chromium."
    ) from error


BASE_URL = os.environ.get("BASE_URL")
CHROME_PATH = os.environ.get("CHROME_PATH")
ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def site_url():
    if BASE_URL is not None:
        url = urlsplit(BASE_URL)
        if url.scheme not in {"http", "https"} or not url.hostname:
            raise ValueError(f"BASE_URL must be an HTTP(S) URL: {BASE_URL!r}")
        yield BASE_URL
        return

    handler = partial(SimpleHTTPRequestHandler, directory=str(ROOT))
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()
            thread.join()


def page_errors(page):
    errors = []
    failed_responses = []
    failed_requests = []
    page.on(
        "console",
        lambda message: errors.append({"text": message.text, "location": message.location})
        if message.type == "error"
        else None,
    )
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on(
        "response",
        lambda response: failed_responses.append(f"{response.status} {response.url}")
        if response.status >= 400
        else None,
    )
    page.on(
        "requestfailed",
        lambda request: failed_requests.append(f"{request.url}: {request.failure}"),
    )
    return errors, failed_responses, failed_requests


def close_dialog(page):
    """Wait for the real close event before using controls restored by its handler."""
    opened = page.locator('dialog[open]')
    if not opened.count():
        page.keyboard.press('Escape')
        return
    opened.evaluate("""el => {
        window.__dialogClosed = false;
        el.addEventListener('close', () => {window.__dialogClosed = true;}, {once:true});
    }""")
    opened.press('Escape')
    page.wait_for_function("window.__dialogClosed && !document.querySelector('dialog[open]')")


def wait_closed(page, selector, action):
    page.locator(selector).evaluate("""el => {
        window.__dialogClosed = false;
        el.addEventListener('close', () => {window.__dialogClosed = true;}, {once:true});
    }""")
    action()
    page.wait_for_function("window.__dialogClosed")
    page.locator(selector).wait_for(state='hidden')


def check_desktop(browser):
    page = browser.new_page(viewport={"width": 1440, "height": 960})
    errors, failed_responses, failed_requests = page_errors(page)
    try:
        page.goto(BASE_URL + "/?internal_test=1", wait_until="networkidle")
        assert page.locator("#hero-title").text_content() == "让技术看得清，让成果走得通。"
        assert page.locator("#capabilities .product").count() == 2
        assert page.locator("main > section").count() == 5
        assert not page.locator("#a2a-dialog").is_visible()
        assert page.locator("main .a2a-workspace").count() == 0
        assert page.locator("#online-tools .tool-card").count() == 4
        for card in page.locator("#capabilities .product").all():
            assert card.locator(".lead").count() == 1
            assert card.locator(".deliverables li").count() == 3
            assert ("订阅 / 定制服务" if card.get_attribute("id") == "tech-insight" else "项目制 / 分阶段推进") in card.inner_text()
        assert page.locator("#hero-title").evaluate("el => getComputedStyle(el).fontSize") == "56px"
        page.get_by_role("link", name="了解两项服务").click()
        page.wait_for_function("location.hash === '#capabilities'")
        products = {"deep-blm": "Deep BLM"}
        assert page.locator('#a2a-product option').evaluate_all("els => els.map(el => el.value)") == ['deep-blm']
        assert page.locator('#demo-dialog').is_hidden()

        opener = page.locator("#open-a2a")
        a2a = page.locator("#a2a-dialog")
        for dismiss in ("escape", "button", "outside"):
            opener.click()
            assert a2a.is_visible()
            assert a2a.locator("[data-close]").evaluate("el => el === document.activeElement")
            page.keyboard.press("Shift+Tab")
            assert a2a.evaluate("el => el.contains(document.activeElement)")
            page.keyboard.press("Tab")
            assert a2a.locator("[data-close]").evaluate("el => el === document.activeElement")
            if dismiss == "escape":
                close_dialog(page)
            elif dismiss == "button":
                wait_closed(page, "#a2a-dialog", lambda: a2a.locator("[data-close]").click())
            else:
                wait_closed(page, "#a2a-dialog", lambda: page.mouse.click(2, 2))
            page.wait_for_function("!document.querySelector('#a2a-dialog').open && document.activeElement.id === 'open-a2a'")

        for service, name in products.items():
            opener.click()
            page.locator("#a2a-product").select_option(service)
            assert "SAMPLE 1 / 5" in page.locator("#a2a-stage-label").inner_text()
            assert page.locator("#a2a-artifact").inner_text() == ""
            for stage in range(2, 6):
                page.locator("#a2a-next").click()
                assert f"SAMPLE {stage} / 5" in page.locator("#a2a-stage-label").inner_text()
                assert page.locator(".stages li[aria-current='step']").count() == 1
            artifact = page.locator("#a2a-artifact").evaluate("el => JSON.parse(el.textContent)")
            assert artifact["service_id"] == service and artifact["service_name"] == name
            assert artifact["sample"] and not artifact["task_executed"] and artifact["findings"] is None
            page.locator("#a2a-intent").click()
            assert not a2a.is_visible()
            assert page.locator("#demand-dialog").is_visible()
            assert page.locator("dialog[open]").count() == 1
            assert name in page.locator("#demand-source").inner_text()
            assert "A2A 意向" in page.locator("#demand-source").inner_text()
            close_dialog(page)
            page.wait_for_function("document.activeElement.id === 'open-a2a'")
            assert opener.is_visible()
            # Generic contact must not inherit the most recently selected sample service.
            page.locator("#contact-a2a").click()
            assert page.locator("#demand-source").inner_text() == "来源：A2A 意向"
            close_dialog(page)
            page.wait_for_function("document.activeElement.id === 'contact-a2a'")
            opener.click()
            page.locator("#a2a-reset").click()
            assert "SAMPLE 1 / 5" in page.locator("#a2a-stage-label").inner_text()
            assert page.locator("#a2a-artifact").inner_text() == ""
            wait_closed(page, "#a2a-dialog", lambda: a2a.locator("[data-close]").click())
            page.wait_for_function("document.activeElement.id === 'open-a2a'")
        opener.click()
        page.locator("#a2a-next").click()
        page.locator("#a2a-reset").click()
        assert "SAMPLE 1 / 5" in page.locator("#a2a-stage-label").inner_text()
        close_dialog(page)
        page.wait_for_function("document.activeElement.id === 'open-a2a'")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert not errors and not failed_responses and not failed_requests, (errors, failed_responses, failed_requests)
    finally:
        page.close()


def check_mobile(browser):
    page = browser.new_page(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
    errors, failed_responses, failed_requests = page_errors(page)
    try:
        # Unavailable storage must not break interactions. No persistence is required.
        page.add_init_script("Object.defineProperty(window, 'localStorage', {get() { throw new Error('fixture: unavailable'); }});")
        page.goto(BASE_URL + "/?internal_test=1", wait_until="networkidle")
        for width in (320, 390, 820, 1440, 1920):
            page.set_viewport_size({"width": width, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
            if width <= 600:
                menu = page.locator(".menu-button")
                assert menu.get_attribute("aria-expanded") == "false"
                menu.click()
                assert menu.get_attribute("aria-expanded") == "true"
                close_dialog(page)
                assert menu.get_attribute("aria-expanded") == "false"
                menu.press("Enter")
                page.locator('#nav-links a[href="#capabilities"]').click()
                page.wait_for_function("location.hash === '#capabilities'")
                assert menu.get_attribute("aria-expanded") == "false"
                menu.click()
                page.locator('#nav-links a[href="#online-tools"]').click()
                page.wait_for_function("location.hash === '#online-tools'")
            for anchor in ("contact-consulting", "contact-partnership", "contact-a2a"):
                page.evaluate("anchor => { location.hash = anchor; }", anchor)
                target = page.locator(f"#{anchor}")
                target.scroll_into_view_if_needed()
                assert target.is_visible()
                target.press("Enter")
                page.locator("#demand-dialog").wait_for(state="visible")
                assert page.locator("#demand-dialog").is_visible()
                close_dialog(page)
            page.locator('#open-insight').click()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
            close_dialog(page)
            page.locator("#open-a2a").click()
            assert page.locator("#a2a-dialog").is_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
            page.locator("#a2a-reset").click()
            for _ in range(4):
                page.locator("#a2a-next").click()
            assert page.locator("#a2a-artifact").is_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
            page.locator("#a2a-intent").click()
            assert not page.locator("#a2a-dialog").is_visible()
            close_dialog(page)
            page.wait_for_function("document.activeElement.id === 'open-a2a'")
        assert page.evaluate("getComputedStyle(document.documentElement).scrollBehavior") == "auto"
        assert not errors and not failed_responses and not failed_requests, (errors, failed_responses, failed_requests)
    finally:
        page.close()
    context = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
    try:
        nojs = context.new_page()
        nojs.goto(BASE_URL, wait_until="networkidle")
        assert nojs.locator("#capabilities .product").count() == 2
        assert nojs.locator("main > section").count() == 5
        assert not nojs.locator("#a2a-dialog").is_visible()
        assert not nojs.locator("#open-a2a").is_visible()
        assert all(card.is_visible() for card in nojs.locator("#capabilities .product").all())
        assert nojs.locator("#capabilities noscript").is_visible()
        assert nojs.locator('a[href="mailto:contact@deeparchi.com.cn"]').count() >= 1
        assert nojs.locator('#nav-links a[href="#contact"]').is_visible()
        assert nojs.evaluate("document.documentElement.scrollWidth <= innerWidth")
    finally:
        context.close()


def check_transfer_entry(browser):
    for javascript in (True, False):
        context = browser.new_context(java_script_enabled=javascript, reduced_motion='reduce', viewport={'width':1440, 'height':960})
        try:
            page = context.new_page()
            errors, responses, failures = page_errors(page)
            page.goto(BASE_URL + '/?internal_test=1', wait_until='networkidle')
            details = page.locator('#transfer-details')
            body = details.locator('p')
            primary = page.locator('#tech-transfer-poc .button.primary')
            assert not details.evaluate('el => el.open')
            # Use the actual main CTA, never a second disclosure as a workaround.
            for activation in ('click', 'Enter', 'Space'):
                if activation == 'click':
                    primary.click()
                else:
                    primary.press(activation)
                assert details.evaluate('el => el.open')
                assert body.is_visible()
                assert '不承诺交易达成、技术验证通过或转化成功' in body.inner_text()
                details.locator('summary').press('Space')
                assert not details.evaluate('el => el.open')
            assert primary.evaluate("el => el.tagName") == 'SUMMARY'
            assert page.locator('#tech-transfer-poc a[href^="#transfer"]').count() == 0
            if javascript:
                # Both primary actions share a desktop baseline and visual hierarchy.
                boxes = [page.locator(selector).bounding_box() for selector in ('#open-insight', '#tech-transfer-poc .primary')]
                assert abs(boxes[0]['y'] - boxes[1]['y']) < 2, boxes
                assert abs(boxes[0]['height'] - boxes[1]['height']) < 2, boxes
                consulting_boxes = [page.locator(selector).bounding_box() for selector in ('#insight-card-consulting', '#transfer-card-consulting')]
                gaps = [consulting_boxes[i]['x'] - (boxes[i]['x'] + boxes[i]['width']) for i in range(2)]
                assert abs(gaps[0] - gaps[1]) < 2, gaps
                consulting = page.locator('#transfer-card-consulting')
                consulting.click()
                assert not details.evaluate('el => el.open')
                assert page.locator('#demand-source').inner_text() == '来源：咨询服务'
                close_dialog(page)
            catalog = page.request.get(BASE_URL + '/service-catalog.json').json()
            href = next(s['details_url'] for s in catalog['services'] if s['id'] == 'tech-transfer-poc')
            page.goto(BASE_URL + '/' + href.replace('#', '?internal_test=1#'), wait_until='networkidle')
            assert details.evaluate('el => el.open')
            assert body.is_visible()
            # Real native links drive same-document hash changes, including reopening.
            for _ in range(2):
                details.locator('summary').click()
                page.locator('#nav-links a[href="#capabilities"]').click()
                page.wait_for_function("location.hash === '#capabilities'")
                page.locator('#nav-links').evaluate("(el, href) => { const a = document.createElement('a'); a.href = href; a.textContent = '目录详情回归'; el.append(a); }", '#' + href.split('#')[1])
                link = page.get_by_role('link', name='目录详情回归')
                link.click()
                page.wait_for_function('(hash) => location.hash === hash', arg='#' + href.split('#')[1])
                assert details.evaluate('el => el.open')
                assert body.is_visible()
                details.locator('summary').click()
                # A repeat activation of the current fragment must also reveal it.
                link.click()
                assert details.evaluate('el => el.open')
                assert body.is_visible()
                link.evaluate('el => el.remove()')
            assert not errors and not responses and not failures, (errors, responses, failures)
        finally:
            context.close()


def check_insight_services(browser):
    services = [
        ("持续洞察与技术雷达服务", "P1 标准订阅", ["季度技术与竞争雷达报告", "重点变化与趋势分析", "业务机会提示", "季度成果交流"]),
        ("深度洞察与专家决策支持服务", "P2 专业订阅", ["季度深度研究报告", "重点专题与竞争比较", "专家针对性建议", "定期专家交流"]),
        ("专项决策与行动支持服务", "P3 定制服务", ["专项分析与论证报告", "解决方案及行动计划", "执行支持成果，按项目需求约定。"]),
    ]
    screenshot_dir = os.environ.get("INSIGHT_SCREENSHOT_DIR")
    if screenshot_dir:
        Path(screenshot_dir).mkdir(parents=True, exist_ok=True)
    for javascript in (True, False):
        context = browser.new_context(java_script_enabled=javascript, reduced_motion="reduce")
        try:
            page = context.new_page()
            errors, failed_responses, failed_requests = page_errors(page)
            outbound = []
            page.on("request", lambda request: outbound.append(request.url) if request.method == "POST" else None)
            page.goto(BASE_URL + "/?internal_test=1", wait_until="networkidle")
            assert page.locator('main > section').evaluate_all("els => els.map(el => el.id)") == ["top", "capabilities", "service-method", "online-tools", "contact"]
            assert page.locator('#insight-services, #nav-links a[href="#insight-services"]').count() == 0
            assert page.locator('#a2a-product option').evaluate_all("els => els.map(el => el.value)") == ['deep-blm']
            assert "Tech M&A" not in page.locator('body').text_content()
            assert page.locator('#tech-ma, [data-service="tech-ma"], [data-demo="tech-insight"]').count() == 0
            card = page.locator('#tech-insight')
            assert card.locator('.badge').inner_text() == '订阅 / 定制服务'
            assert card.locator('.actions > *').all_text_contents() == ['了解服务', '咨询服务']
            opener = page.locator('#open-insight')
            dialog = page.locator('#insight-dialog')
            fallback = page.locator('#insight-details')
            assert not dialog.is_visible()
            for width in (320, 390, 820, 1440, 1920):
                page.set_viewport_size({"width": width, "height": 960})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (javascript, width)
                # Equal service columns on desktop; compact four/two-column tool grid.
                boxes = [el.bounding_box() for el in page.locator('#capabilities .product').all()]
                tools = [el.bounding_box() for el in page.locator('#online-tools .tool-card').all()]
                assert len(boxes) == 2 and len(tools) == 4
                assert abs(boxes[0]['width'] - boxes[1]['width']) < 2
                if width > 900:
                    assert abs(boxes[0]['y'] - boxes[1]['y']) < 2
                    assert abs(boxes[0]['height'] - boxes[1]['height']) < 2
                    assert all(abs(tool['y'] - tools[0]['y']) < 2 for tool in tools)
                else:
                    assert boxes[1]['y'] > boxes[0]['y']
                    assert abs(tools[0]['y'] - tools[1]['y']) < 2
                    assert abs(tools[2]['y'] - tools[3]['y']) < 2
                    assert tools[2]['y'] > tools[0]['y']
                assert page.locator('#online-tools #integrate #open-a2a').count() == 1
                assert '运行中的 A2A 端点' in page.locator('#online-tools').inner_text()
                transfer = page.locator('#transfer-details')
                if not transfer.evaluate('el => el.open'):
                    transfer.locator('summary').click()
                assert '不承诺交易达成、技术验证通过或转化成功' in transfer.inner_text()
                transfer.locator('summary').click()
                assert page.locator('#hero-title').text_content() == '让技术看得清，让成果走得通。'
                for selector in ('.hero', '.section-heading', '#integrate', '#contact'):
                    for element in page.locator(selector).all():
                        assert element.evaluate('el => getComputedStyle(el).textAlign') == 'center', (width, selector)
                for selector in ('.hero .actions', '.signal-choice', '#contact .actions', '.contact-shortcuts'):
                    assert page.locator(selector).evaluate('el => getComputedStyle(el).justifyContent') == 'center', (width, selector)
                assert page.locator('#capabilities').evaluate("el => getComputedStyle(el).backgroundColor") == 'rgb(255, 255, 255)'
                assert page.locator('body').evaluate("el => getComputedStyle(el).getPropertyValue('--blue').trim()") == '#0066cc'
                assert page.locator('body').evaluate("el => getComputedStyle(el).getPropertyValue('--hover').trim()") == '#0055ad'
                assert page.locator('.hero .primary').evaluate('el => getComputedStyle(el).backgroundColor') == 'rgb(0, 102, 204)'
                for cta in page.locator('#online-tools a.button').all():
                    assert cta.get_attribute('class') == 'button outline'
                    assert cta.evaluate('el => getComputedStyle(el).borderColor') == 'rgb(0, 102, 204)'
                    assert cta.bounding_box()['height'] >= 44
                for selector, minimum in (('#online-tools .tool-card > p:not(.tool-hint)', 14), ('#online-tools .tool-hint', 13), ('#online-tools a.button, #online-tools button.button', 14), ('#online-tools .section-heading > p:last-child, #integrate .panel-copy', 14), ('#integrate .concept-note', 13)):
                    elements = page.locator(selector).all()
                    assert elements, selector
                    for element in elements:
                        size = element.evaluate('el => parseFloat(getComputedStyle(el).fontSize)')
                        assert size >= minimum, (javascript, width, selector, size, minimum)
                assert page.locator('#online-tools .tool-card h3').all_text_contents() == ['Deep BLM', '专利体检', '制裁与出口管制速查', 'Source Slide Editor']
                assert page.locator('#online-tools #deep-blm a.button').inner_text() == '打开规划工具（试用）'
                for removed in ('技术架构规划', 'IP 守护', 'ip-guard', 'sourceIP', 'architecture'):
                    assert removed not in page.locator('body').text_content()
                opener.click()
                if javascript:
                    assert dialog.is_visible() and not fallback.is_visible()
                    assert dialog.get_attribute('aria-labelledby') == 'insight-title'
                    assert dialog.locator('[data-close]').evaluate('el => el === document.activeElement')
                    page.keyboard.press('Shift+Tab')
                    assert dialog.evaluate('el => el.contains(document.activeElement)')
                    page.keyboard.press('Tab')
                    assert dialog.locator('[data-close]').evaluate('el => el === document.activeElement')
                    content = dialog
                    rect = dialog.bounding_box()
                    assert rect['x'] >= 0 and rect['x'] + rect['width'] <= width
                    assert rect['y'] >= 0 and rect['y'] + rect['height'] <= 960
                    assert dialog.evaluate('el => el.scrollWidth <= el.clientWidth')
                else:
                    assert fallback.is_visible()
                    # The fragment reveals the disclosure entry; summary opens the full text.
                    if not fallback.evaluate('el => el.open'):
                        fallback.locator('summary').click()
                    content = fallback
                    assert not page.locator('#insight-consulting').is_visible()
                assert '持续洞察变化，支持科学决策，推动业务创新' in content.inner_text()
                assert 'P1、P2采用持续订阅模式；P3根据具体项目需求定制。具体服务范围、交付周期与成果形式以双方约定为准。' in content.inner_text()
                for index, (name, mode, deliverables) in enumerate(services):
                    service = content.locator('.insight-card').nth(index)
                    assert service.get_by_role('heading', name=name, exact=True).is_visible()
                    assert ' '.join(service.locator('.insight-mode').inner_text().split()) == mode
                    assert service.get_attribute('aria-labelledby') == service.locator('h3').get_attribute('id')
                    assert service.locator('li').all_inner_texts() == deliverables
                    assert all(item.is_visible() for item in service.locator('li').all())
                    assert service.evaluate('el => el.scrollWidth <= el.clientWidth')
                    assert float(service.evaluate('el => parseFloat(getComputedStyle(el).fontSize)')) >= 16
                assert content.locator('.insight-strengths dt').all_inner_texts() == ['持续跟踪', 'AI＋专家', '业务导向']
                email = content.get_by_role('link', name='邮件咨询：contact@deeparchi.com.cn', exact=True)
                assert email.is_visible() and email.get_attribute('href') == 'mailto:contact@deeparchi.com.cn'
                if screenshot_dir:
                    content.screenshot(path=str(Path(screenshot_dir) / f'insight-{width}-{"js" if javascript else "nojs"}.png'))
                if javascript:
                    for dismiss in ('escape', 'button', 'outside'):
                        if not dialog.is_visible():
                            opener.click()
                        # Native focus may restore before the queued close event runs.
                        # Wait for the real event, not just an already-true focus snapshot.
                        page.evaluate("""() => {
                            window.__insightClosed = false;
                            document.querySelector('#insight-dialog').addEventListener('close',
                                () => {window.__insightClosed = true;}, {once:true});
                        }""")
                        if dismiss == 'escape':
                            close_dialog(page)
                        elif dismiss == 'button':
                            dialog.locator('[data-close]').click()
                        else:
                            page.mouse.click(2, 2)
                        page.wait_for_function("() => window.__insightClosed && !document.querySelector('#insight-dialog').open && document.activeElement.id === 'open-insight'")
                    for selector in ('#insight-card-consulting', '#insight-consulting'):
                        if selector == '#insight-consulting':
                            opener.click()
                        cta = page.locator(selector)
                        assert cta.get_attribute('data-service') is None
                        cta.press('Enter')
                        page.locator('#demand-dialog').wait_for(state='visible')
                        assert page.locator('#demand-dialog').is_visible()
                        assert page.locator('dialog[open]').count() == 1
                        assert page.locator('#demand-source').inner_text() == '来源：咨询服务'
                        page.locator('#problem').fill('咨询技术与战略洞察服务')
                        page.locator('#demand-form button[type="submit"]').click()
                        assert '咨询服务' in page.locator('#draft-text').inner_text()
                        assert 'Tech M&A' not in page.locator('#draft-text').inner_text()
                        page.evaluate("""() => {
                            window.__demandClosed = false;
                            document.querySelector('#demand-dialog').addEventListener('close',
                                () => {window.__demandClosed = true;}, {once:true});
                        }""")
                        close_dialog(page)
                        target = 'open-insight' if selector == '#insight-consulting' else 'insight-card-consulting'
                        page.wait_for_function('(id) => window.__demandClosed && document.activeElement.id === id', arg=target)
                else:
                    fallback.locator('summary').click()
                    assert not fallback.evaluate('el => el.open')
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (javascript, width)
            # Machine catalogue direct detail links work with either scripting mode.
            page.goto(BASE_URL + '/?internal_test=1#insight-details', wait_until='networkidle')
            if javascript:
                assert dialog.is_visible()
                close_dialog(page)
                page.wait_for_function("document.activeElement.id === 'open-insight'")
            else:
                assert fallback.locator('summary').is_visible()
            catalogue = page.request.get(BASE_URL + '/service-catalog.json').json()
            assert [service['id'] for service in catalogue['services']] == ['tech-insight', 'tech-transfer-poc']
            assert [tool['id'] for tool in catalogue['tools']] == ['deep-blm', 'patent-health', 'sanctions-quickcheck', 'source-slide-editor']
            assert catalogue['a2a'] == {'available': False, 'endpoint': None}
            assert outbound == []
            assert not errors and not failed_responses and not failed_requests, (errors, failed_responses, failed_requests)
        finally:
            context.close()


def check_contact_paths(browser):
    page = browser.new_page(viewport={"width": 1440, "height": 960}, reduced_motion="reduce")
    errors, failed_responses, failed_requests = page_errors(page)
    outbound = []
    page.on("request", lambda request: outbound.append(request.url) if request.method == "POST" or request.url.startswith("mailto:") else None)
    try:
        page.goto(BASE_URL + "/?internal_test=1", wait_until="networkidle")
        # Clipboard denial is an explicit fixture, not a successful system clipboard claim.
        page.evaluate("Object.defineProperty(navigator, 'clipboard', {value: {writeText: async () => {throw new Error('fixture denial');}}, configurable:true})")
        routes = [('#transfer-card-consulting','咨询服务'),('#insight-card-consulting','咨询服务'),('.contact-shortcuts [data-intent="consulting"]','咨询服务'),('.contact-shortcuts [data-intent="integration"]','工具集成'),('#contact [data-intent="general"]','通用需求'),('#contact-consulting','咨询服务'),('#contact-partnership','伙伴合作'),('#contact-a2a','A2A 意向')]
        user_text = '<img src=x onerror="window.BAD=true"> + 商业问题 & 第二行'
        for selector, source in routes:
            trigger = page.locator(selector)
            trigger.click()
            assert source in page.locator("#demand-source").inner_text()
            if selector == '#contact-a2a':
                assert page.locator('#demand-source').inner_text() == '来源：A2A 意向'
            page.locator('#demand-form button[type="submit"]').click()
            assert not page.locator("#draft").is_visible()
            assert not page.locator("#problem").evaluate("el => el.checkValidity()")
            page.locator("#problem").fill("   ")
            page.locator('#demand-form button[type="submit"]').click()
            assert not page.locator("#draft").is_visible()
            page.locator("#problem").fill(user_text)
            page.locator("#result").fill("明确可核验的结果")
            page.locator("#constraints").fill("约束样例")
            page.locator('#demand-form button[type="submit"]').click()
            assert page.locator("#draft").is_visible()
            assert "尚未发送" in page.locator("#draft").inner_text()
            href = page.locator("#draft-mailto").get_attribute("href")
            url = urlsplit(href)
            assert url.scheme == "mailto" and url.path == "contact@deeparchi.com.cn"
            values = parse_qs(url.query)
            assert source in values["subject"][0] and user_text in values["body"][0]
            assert "%20" in href and "+" not in href and not url.fragment
            assert page.locator("#draft-text img").count() == 0
            assert page.evaluate("window.BAD === undefined")
            assert "商业问题" not in page.url
            page.locator("#copy-draft").click()
            assert "手动复制" in page.locator("#copy-status").inner_text()
            # Observe explicit mailto activation without launching an OS mail client.
            page.locator("#draft-mailto").evaluate("el => el.addEventListener('click', e => e.preventDefault(), {once:true})")
            page.locator("#draft-mailto").click()
            page.locator("#result").fill("修改后需重新准备")
            assert not page.locator("#draft").is_visible()
            assert page.locator("#draft-mailto").get_attribute("href") is None
            close_dialog(page)
            page.wait_for_function("document.querySelector('#problem').value === ''")
            assert trigger.evaluate("el => el === document.activeElement")
            assert page.locator("#problem").input_value() == ""
        page.locator('#contact-a2a').click()
        page.locator('#problem').fill('长' * 500)
        page.locator('#result').fill('果' * 500)
        page.locator('#constraints').fill('限' * 300)
        page.locator('#demand-form button[type="submit"]').click()
        assert '较长' in page.locator('#copy-status').inner_text()
        assert '粘贴' in page.locator('#draft-mailto').inner_text()
        assert page.locator('#copy-draft').evaluate("el => el.classList.contains('primary')")
        assert 'body' not in parse_qs(urlsplit(page.locator('#draft-mailto').get_attribute('href')).query)
        assert '长' * 500 in page.locator('#draft-text').inner_text()
        close_dialog(page)
        page.wait_for_function("document.querySelector('#demand-dialog').open === false")
        page.locator('#open-insight').click()
        page.locator("#insight-consulting").click()
        assert page.locator("#demand-source").inner_text() == "来源：咨询服务"
        page.mouse.click(2, 2)
        assert not page.locator("#demand-dialog").is_visible()
        page.wait_for_function("document.activeElement.id === 'open-insight'")
        assert page.locator("#open-insight").evaluate("el => el === document.activeElement")
        page.locator("#copy-email").click()
        assert "contact@deeparchi.com.cn" in page.locator("#email-status").inner_text()
        assert '请勿发送敏感数据、密码或密钥' in page.locator('#contact-data-warning').inner_text()
        assert page.locator('#contact a[href="mailto:contact@deeparchi.com.cn"]').is_visible()
        assert outbound == [], outbound

        # Enabled config is a test fixture; local/test guards still forbid real transport.
        page.route("**/analytics-config.json", lambda route: route.fulfill(json={"version":"1","enabled":True,"endpoint":"https://metrics.example.org/receive","consent_required":True}))
        page.goto(BASE_URL + "/?internal_test=1", wait_until="networkidle")
        panel = page.locator("footer [data-analytics]")
        banner = page.locator("[data-analytics-banner]")
        assert banner.is_visible()
        assert banner.locator('a[href="privacy.html"]').is_visible()
        assert page.locator('[data-analytics-feedback]').inner_text() == ''
        banner.locator('[data-consent="reject"]').click()
        assert not banner.is_visible()
        assert page.locator('[data-analytics-feedback]').is_visible()
        assert '未获同意' in page.locator('[data-analytics-feedback]').inner_text()
        panel.locator("summary").click()
        assert "未获同意" in panel.inner_text()
        panel.locator('[data-consent="reject"]').click()
        assert "未获同意" in panel.inner_text()
        panel.locator('[data-consent="accept"]').click()
        assert "已允许" in panel.inner_text()
        assert '已允许' in page.locator('[data-analytics-feedback]').inner_text()
        page.locator('#open-insight').click()
        close_dialog(page)
        assert outbound == []
        # Reconfigure only in explicit internal-test mode with an in-memory fixture transport.
        # This records actual UI handlers (including a user-entered draft), not a live receiver.
        page.evaluate("""async () => {
            const {initAnalytics} = await import(document.querySelector('script[type="module"]').src);
            window.fixtureEvents = [];
            await initAnalytics({transport:async (endpoint, payload) => {
                window.fixtureEvents.push(payload); return {ok:true};
            }});
        }""")
        panel.locator('[data-consent="reject"]').click()
        # Exercise a real tracked tool entry while preventing navigation in this fixture.
        denied_entry = page.locator('#deep-blm [data-tool-entry="deep-blm"]')
        denied_entry.evaluate("el => el.addEventListener('click', e => e.preventDefault(), {once:true})")
        denied_entry.press('Enter')
        assert page.evaluate("window.fixtureEvents.length") == 0
        page.locator('#deep-blm').scroll_into_view_if_needed()
        # Invoke the actual consent handler without Playwright scrolling back to the footer.
        assert page.locator('#deep-blm').evaluate("el => {const r=el.getBoundingClientRect();return Math.max(0,Math.min(innerHeight,r.bottom)-Math.max(0,r.top)) >= r.height*.5;}")
        panel.locator('[data-consent="accept"]').evaluate("el => el.click()")
        assert any(event['event'] == 'product_view' for event in page.evaluate('window.fixtureEvents'))
        page.locator('#tech-insight').scroll_into_view_if_needed()
        panel.locator('[data-consent="accept"]').evaluate('el => el.click()')
        page.locator('#insight-card-consulting').click()
        close_dialog(page)
        page.wait_for_function("window.fixtureEvents.some(e => e.event === 'intent_open' && e.category === 'consulting' && e.surface === 'cards' && e.service === null)")
        page.locator('#transfer-card-consulting').click()
        assert page.locator('#demand-source').inner_text() == '来源：咨询服务'
        assert page.locator('dialog[open]').count() == 1
        close_dialog(page)
        page.wait_for_function("document.activeElement.id === 'transfer-card-consulting'")
        assert all(event['service'] is None for event in page.evaluate('window.fixtureEvents') if event['category'] == 'consulting')
        # Opening a static sample is neither completed work nor confirmed intent.
        # Scrolling can legitimately produce card views; inspect only actions tied to the sample.
        sample_events = "window.fixtureEvents.filter(e => ['a2a_step','a2a_interest','intent_open','demo_complete'].includes(e.event))"
        before_sample = page.evaluate(sample_events)
        page.locator('#open-a2a').click()
        close_dialog(page)
        page.wait_for_function("document.activeElement.id === 'open-a2a'")
        assert page.evaluate(sample_events) == before_sample
        page.locator('#open-a2a').click()
        page.locator('#a2a-product').select_option('deep-blm')
        for _ in range(4):
            page.locator('#a2a-next').click()
        page.locator('#a2a-intent').click()
        assert page.locator('#demand-source').inner_text() == '来源：A2A 意向 / Deep BLM'
        assert not page.locator('#a2a-dialog').is_visible()
        close_dialog(page)
        page.wait_for_function("document.activeElement.id === 'open-a2a'")
        page.locator('#open-a2a').click()
        assert 'SAMPLE 1 / 5' in page.locator('#a2a-stage-label').inner_text()
        assert not page.locator('#a2a-artifact').is_visible()
        assert not page.locator('#a2a-intent').is_visible()
        close_dialog(page)
        page.locator('#open-insight').click()
        page.locator("#insight-consulting").click()
        page.locator("#problem").fill(user_text)
        page.locator('#demand-form button[type="submit"]').click()
        page.locator("#draft-mailto").evaluate("el => el.addEventListener('click', e => e.preventDefault(), {once:true})")
        page.locator("#draft-mailto").click()
        close_dialog(page)
        page.wait_for_function("document.querySelector('#demand-dialog').open === false")
        page.locator('#contact-a2a').click()
        assert page.locator('#demand-source').inner_text() == '来源：A2A 意向'
        close_dialog(page)
        page.locator('button[data-intent="integration"]').click()
        assert page.locator('#demand-source').inner_text() == '来源：工具集成'
        close_dialog(page)
        page.locator('#open-insight').click()
        page.locator('#insight-consulting').click()
        assert page.locator('#demand-source').inner_text() == '来源：咨询服务'
        close_dialog(page)
        page.wait_for_function("window.fixtureEvents.some(e => e.event === 'intent_open' && e.category === 'a2a' && e.service === null) && window.fixtureEvents.some(e => e.event === 'mailto_click') && window.fixtureEvents.some(e => e.event === 'intent_open' && e.category === 'integration')")
        page.wait_for_function("window.fixtureEvents.some(e => e.event === 'intent_open' && e.category === 'consulting' && e.surface === 'support' && e.service === null)")
        # Moving Deep BLM preserves its registered card and entry event identities.
        # Prevent navigation only in this transport fixture; real routes are tested separately.
        page.locator('#deep-blm').scroll_into_view_if_needed()
        panel.locator('[data-consent="accept"]').evaluate('el => el.click()')
        page.wait_for_function("window.fixtureEvents.some(e => e.event === 'product_view' && e.service === 'deep-blm')")
        tool_entry = page.locator('#deep-blm [data-tool-entry="deep-blm"]')
        assert tool_entry.get_attribute('data-demo') == 'deep-blm'
        tool_entry.evaluate("el => el.addEventListener('click', e => e.preventDefault(), {once:true})")
        tool_entry.press('Enter')
        page.wait_for_function("window.fixtureEvents.some(e => e.event === 'demo_open' && e.service === 'deep-blm' && e.surface === 'cards')")
        for identity in ('patent-health', 'sanctions-quickcheck', 'source-slide-editor'):
            tool = page.locator(f'#online-tools #{identity}')
            tool.scroll_into_view_if_needed()
            panel.locator('[data-consent="accept"]').evaluate('el => el.click()')
            assert tool.locator('[data-demo], [data-service], [data-intent]').count() == 0
            link = tool.locator('a.button')
            link.evaluate("el => el.addEventListener('click', e => e.preventDefault(), {once:true})")
            link.press('Enter')
        assert page.locator('dialog[open]').count() == 0
        recorded = page.evaluate("window.fixtureEvents")
        assert all(event['service'] in (None, 'deep-blm') for event in recorded)
        assert any(event['event'] == 'intent_open' and event['category'] == 'a2a' and event['service'] is None for event in recorded)
        assert any(event['event'] == 'intent_open' and event['category'] == 'a2a' and event['service'] == 'deep-blm' and event['surface'] == 'a2a' for event in recorded)
        assert any(event['event'] == 'intent_open' and event['category'] == 'integration' and event['surface'] == 'contact' and event['service'] is None for event in recorded)
        assert not any(event['event'] == 'a2a_interest' and event['surface'] == 'contact' for event in recorded)
        assert {"demo_open", "intent_open", "mail_draft_ready", "mailto_click"}.issubset({event["event"] for event in recorded})
        assert all(event['event'] != 'demo_complete' for event in recorded)
        assert all(event['service'] not in ('ip-guard', 'architecture', 'tech-ma', 'tech-insight', 'tech-transfer-poc', 'patent-health', 'sanctions-quickcheck', 'source-slide-editor') for event in recorded)
        assert {e['service'] for e in recorded if e['event'] == 'product_view'} <= {'deep-blm'}
        assert any(event['event'] == 'intent_open' and event['category'] == 'consulting' and event['service'] is None and event['surface'] == 'cards' for event in recorded)
        assert all(event['service'] is None for event in recorded if event['category'] == 'consulting')
        allowed = {"event", "service", "category", "surface", "version", "audience", "is_test", "session_id", "event_id", "step", "source_origin", "source_state"}
        assert all(set(event) <= allowed and event["is_test"] is True and event["audience"] == "browser_interaction" for event in recorded)
        assert user_text not in str(recorded) and "商业问题" not in str(recorded)
        panel.locator('[data-consent="reject"]').click()
        count = page.evaluate("window.fixtureEvents.length")
        # A fresh intent identity must still be suppressed after consent is revoked.
        page.locator('#contact [data-intent="general"]').click()
        close_dialog(page)
        assert page.evaluate("window.fixtureEvents.length") == count
        assert "未获同意" in panel.inner_text()
        assert outbound == []
        assert not errors and not failed_responses and not failed_requests, (errors, failed_responses, failed_requests)
    finally:
        page.close()
    for privacy_flag in ("doNotTrack", "globalPrivacyControl"):
        context = browser.new_context()
        try:
            context.add_init_script(f"Object.defineProperty(navigator, '{privacy_flag}', {{get: () => {repr('1') if privacy_flag == 'doNotTrack' else 'true'}}});")
            context.route("**/analytics-config.json", lambda route: route.fulfill(json={"version":"1","enabled":True,"endpoint":"https://metrics.example.org/receive","consent_required":True}))
            protected = context.new_page()
            requests = []
            protected.on("request", lambda request: requests.append(request.url) if request.method == "POST" else None)
            protected.goto(BASE_URL + "/?internal_test=1", wait_until="networkidle")
            protected.locator("footer [data-analytics] summary").click()
            assert "DNT/GPC" in protected.locator("footer [data-analytics]").inner_text()
            assert not protected.locator("footer [data-analytics-options]").is_visible()
            assert not protected.locator("[data-analytics-banner]").is_visible()
            protected.locator('#open-a2a').click()
            protected.locator('#a2a-next').click()
            close_dialog(protected)
            assert requests == []
        finally:
            context.close()


def check_tool_routes(browser):
    tools = [
        ('deep-blm', '/apps/deepblm.html', '#workspace', 'Deep BLM'),
        ('patent-health', '/apps/patent-health-selfcheck.html', '#form input', '专利体检'),
        ('sanctions-quickcheck', '/apps/sanctions-quickcheck.html', '#companyName', '制裁与出口管制速查'),
        ('source-slide-editor', '/apps/source-slide-editor/', '#app #welcome', 'Source Slide Editor'),
    ]
    context = browser.new_context(viewport={'width':1440, 'height':960}, reduced_motion='reduce')
    outbound = []
    origin = urlsplit(BASE_URL).netloc
    def local_shell_only(route):
        request = route.request
        if urlsplit(request.url).netloc != origin or request.method != 'GET':
            outbound.append(request.url)
            route.abort()
        else:
            route.continue_()
    context.route('**/*', local_shell_only)
    try:
        page = context.new_page()
        errors, responses, failures = page_errors(page)
        for identity, path, shell, title in tools:
            page.goto(BASE_URL + '/?internal_test=1', wait_until='networkidle')
            link = page.locator(f'#online-tools #{identity} a.button')
            assert link.count() == 1
            link.press('Enter')
            page.wait_for_url(lambda url: urlsplit(str(url)).path == path)
            page.wait_for_load_state('networkidle')
            assert title in page.title()
            page.locator(shell).first.wait_for(state='visible')
            assert not outbound, outbound
        assert not errors and not responses and not failures, (errors, responses, failures)
    finally:
        context.close()


def check_forced_colors(browser):
    context = browser.new_context(forced_colors='active', reduced_motion='reduce', viewport={'width':390,'height':844})
    try:
        page = context.new_page()
        page.goto(BASE_URL + '/?internal_test=1', wait_until='networkidle')
        assert page.evaluate("matchMedia('(forced-colors: active)').matches")
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        for card in page.locator('#capabilities .product, #online-tools .tool-card').all():
            assert card.evaluate("el => getComputedStyle(el).borderTopStyle") == 'solid'
        page.locator('#open-insight').press('Enter')
        page.locator('#insight-dialog').wait_for(state='visible')
        close_dialog(page)
        assert page.locator('#open-insight').evaluate('el => el === document.activeElement')
    finally:
        context.close()


def check_official_brand(browser):
    base_url = BASE_URL
    assert base_url is not None
    page = browser.new_page(viewport={"width": 1440, "height": 960})
    errors, failed_responses, failed_requests = page_errors(page)
    screenshot_dir = os.environ.get("BRAND_SCREENSHOT_DIR")
    if screenshot_dir:
        Path(screenshot_dir).mkdir(parents=True, exist_ok=True)
    try:
        for document in ("index.html", "developers.html", "privacy.html"):
            page.goto(base_url + "/" + document + "?internal_test=1", wait_until="networkidle")
            logo = page.locator(".brand-logo")
            assert logo.count() == 1 and logo.is_visible(), document
            assert logo.get_attribute("src") == "assets/deeparchi-logo.png"
            assert logo.get_attribute("alt") == "DeepArchi 公司标志"
            dimensions = logo.evaluate("img => ({ready: img.complete, w: img.naturalWidth, h: img.naturalHeight})")
            assert dimensions == {"ready": True, "w": 498, "h": 512}, (document, dimensions)
            favicon = page.locator('link[rel="icon"]')
            assert favicon.get_attribute("href") == "assets/deeparchi-favicon.png"
            loaded = page.evaluate("""async href => {
                const response = await fetch(href);
                const bytes = new Uint8Array(await response.arrayBuffer());
                return {status: response.status, signature: Array.from(bytes.slice(0, 8))};
            }""", favicon.get_attribute("href"))
            assert loaded == {"status": 200, "signature": [137, 80, 78, 71, 13, 10, 26, 10]}, document
            for width in (320, 390, 820, 1440, 1920):
                page.set_viewport_size({"width": width, "height": 960})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (document, width)
                bounds = logo.bounding_box()
                header = page.locator(".site-header").bounding_box()
                assert bounds and header and bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= width
                assert bounds["y"] >= header["y"] and bounds["y"] + bounds["height"] <= header["y"] + header["height"]
                assert abs(bounds["width"] / bounds["height"] - 498 / 512) < 0.005, (document, width)
                assert bounds["height"] == 88, (document, width)
                assert logo.evaluate("el => getComputedStyle(el).objectFit") == "contain"
                assert page.locator(".site-header").evaluate("el => getComputedStyle(el).backgroundColor") == "rgb(255, 255, 255)"
                if document == "index.html":
                    page.locator('#nav-links a[href="#capabilities"]').evaluate("el => el.click()")
                    page.wait_for_function("location.hash === '#capabilities'")
                    page.wait_for_function("""() => {
                        const top = document.querySelector('#capabilities').getBoundingClientRect().top;
                        const clearance = parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop);
                        return Math.abs(top - clearance) < 2 && top >= document.querySelector('.site-header').getBoundingClientRect().bottom;
                    }""")
                    page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
                if screenshot_dir and width in (390, 1440):
                    page.screenshot(path=str(Path(screenshot_dir) / f"{Path(document).stem}-{width}.png"))
        assert not errors and not failed_responses and not failed_requests, (errors, failed_responses, failed_requests)
    finally:
        page.close()


if __name__ == "__main__":
    if CHROME_PATH is not None and not Path(CHROME_PATH).is_file():
        raise FileNotFoundError(f"CHROME_PATH is not a file: {CHROME_PATH!r}")

    with site_url() as BASE_URL:
        print(f"Testing {BASE_URL}", flush=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=CHROME_PATH, headless=True)
            try:
                check_transfer_entry(browser)
                print('PASS: real native transfer CTA, repeated opening, catalog initial fragment and same-page/repeated fragments, JS/no-JS', flush=True)
                check_insight_services(browser)
                print("PASS: two equal professional services + compact four/two-column tools + one A2A sample — full insight dialog, generic consultation, responsive grids at 320/390/820/1440/1920, no-JS", flush=True)
                check_official_brand(browser)
                print("PASS: official logo and favicon — all three pages, image decode, proportional sizing, 320/390/820/1440", flush=True)
                check_desktop(browser)
                print("PASS: desktop — two labelled sample dialogs and native Deep BLM entry, focus restoration, all A2A sample stages/reset/product changes", flush=True)
                check_mobile(browser)
                print("PASS: 320/390/820/1440/1920 — no overflow, navigation, keyboard, reduced motion, unavailable storage, no-JS", flush=True)
                check_tool_routes(browser)
                print("PASS: all four native tool routes render their real local shells; no query/upload/provider calls", flush=True)
                check_forced_colors(browser)
                print("PASS: forced colors, reduced motion and keyboard dialog entry", flush=True)
                check_contact_paths(browser)
                print("PASS: demand sources, validation, safe mail drafts, clipboard fallback, consent/DNT/GPC fixtures; no real analytics transport", flush=True)
            finally:
                browser.close()
