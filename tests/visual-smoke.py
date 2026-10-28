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


def check_desktop(browser):
    page = browser.new_page(viewport={"width": 1440, "height": 960})
    errors, failed_responses, failed_requests = page_errors(page)
    try:
        page.goto(BASE_URL + "/?internal_test=1", wait_until="networkidle")
        assert "让重要的专业服务" in page.locator("#hero-title").inner_text()
        page.get_by_role("link", name="查看服务 Demo").click()
        page.wait_for_function("location.hash === '#capabilities'")
        products = {"ip-guard": "IP 守护", "deep-blm": "Deep BLM", "architecture": "技术架构规划", "tech-ma": "Tech M&A"}
        for service, name in products.items():
            trigger = page.locator(f'[data-demo="{service}"]')
            trigger.click()
            dialog = page.locator("#demo-dialog")
            assert dialog.is_visible()
            assert page.locator("#demo-title").inner_text() == name
            assert "演示样例，非真实客户交付" in dialog.inner_text()
            assert "虚构团队" in page.locator("#demo-problem").inner_text()
            assert page.locator("#demo-output li").count() == 3
            page.keyboard.press("Escape")
            assert not dialog.is_visible()
            assert trigger.evaluate("element => element === document.activeElement")
            trigger.click()
            dialog.locator("[data-close]").click()
            assert trigger.evaluate("element => element === document.activeElement")
        page.locator('[data-demo="ip-guard"]').click()
        page.mouse.click(2, 2)
        assert not page.locator("#demo-dialog").is_visible()
        assert page.locator('[data-demo="ip-guard"]').evaluate("el => el === document.activeElement")

        for service, name in products.items():
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
            assert name in page.locator("#demand-source").inner_text()
            assert "A2A 意向" in page.locator("#demand-source").inner_text()
            page.keyboard.press("Escape")
            assert page.locator("#a2a-intent").evaluate("el => el === document.activeElement")
            page.locator("#a2a-reset").click()
            assert "SAMPLE 1 / 5" in page.locator("#a2a-stage-label").inner_text()
            assert page.locator("#a2a-artifact").inner_text() == ""
        page.locator("#a2a-next").click()
        page.locator("#a2a-product").select_option("ip-guard")
        assert "SAMPLE 1 / 5" in page.locator("#a2a-stage-label").inner_text()
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
        for width in (320, 390, 820, 1440):
            page.set_viewport_size({"width": width, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
            if width <= 600:
                menu = page.locator(".menu-button")
                assert menu.get_attribute("aria-expanded") == "false"
                menu.click()
                assert menu.get_attribute("aria-expanded") == "true"
                page.keyboard.press("Escape")
                assert menu.get_attribute("aria-expanded") == "false"
                menu.focus()
                page.keyboard.press("Enter")
                page.locator('#nav-links a[href="#capabilities"]').click()
                page.wait_for_function("location.hash === '#capabilities'")
                assert menu.get_attribute("aria-expanded") == "false"
                menu.click()
                page.locator('#nav-links a[href="#integrate"]').click()
                page.wait_for_function("location.hash === '#integrate'")
            for anchor in ("contact-consulting", "contact-partnership", "contact-a2a"):
                page.evaluate("anchor => { location.hash = anchor; }", anchor)
                target = page.locator(f"#{anchor}")
                target.scroll_into_view_if_needed()
                assert target.is_visible()
                target.focus()
                page.keyboard.press("Enter")
                assert page.locator("#demand-dialog").is_visible()
                page.keyboard.press("Escape")
            page.locator('[data-demo="architecture"]').click()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
            page.keyboard.press("Escape")
        assert page.evaluate("getComputedStyle(document.documentElement).scrollBehavior") == "auto"
        assert not errors and not failed_responses and not failed_requests, (errors, failed_responses, failed_requests)
    finally:
        page.close()
    context = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
    try:
        nojs = context.new_page()
        nojs.goto(BASE_URL, wait_until="networkidle")
        assert nojs.locator(".product").count() == 4
        assert all(card.is_visible() for card in nojs.locator(".product").all())
        assert nojs.locator("noscript").is_visible()
        assert nojs.locator('a[href="mailto:contact@deeparchi.com.cn"]').count() >= 1
        assert nojs.locator('#nav-links a[href="#contact"]').is_visible()
        assert nojs.evaluate("document.documentElement.scrollWidth <= innerWidth")
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
        routes = [(f'.product [data-service="{service}"]', name) for service, name in [("ip-guard","IP 守护"),("deep-blm","Deep BLM"),("architecture","技术架构规划"),("tech-ma","Tech M&A")]]
        routes += [('.support [data-intent="consulting"]','咨询服务'),('.support [data-intent="integration"]','工具集成'),('#contact [data-intent="general"]','通用需求'),('#contact-consulting','咨询服务'),('#contact-partnership','伙伴合作'),('#contact-a2a','A2A 意向')]
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
            page.keyboard.press("Escape")
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
        page.keyboard.press('Escape')
        page.wait_for_function("document.querySelector('#demand-dialog').open === false")
        page.locator('[data-demo="deep-blm"]').click()
        page.locator("#demo-intent").click()
        assert "产品需求 / Deep BLM" in page.locator("#demand-source").inner_text()
        page.mouse.click(2, 2)
        assert not page.locator("#demand-dialog").is_visible()
        assert page.locator('[data-demo="deep-blm"]').evaluate("el => el === document.activeElement")
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
        banner.locator('[data-consent="reject"]').click()
        assert not banner.is_visible()
        panel.locator("summary").click()
        assert "未获同意" in panel.inner_text()
        panel.locator('[data-consent="reject"]').click()
        assert "未获同意" in panel.inner_text()
        panel.locator('[data-consent="accept"]').click()
        assert "已允许" in panel.inner_text()
        page.locator('[data-demo="ip-guard"]').click()
        page.keyboard.press("Escape")
        assert outbound == []
        # Reconfigure only in explicit internal-test mode with an in-memory fixture transport.
        # This records actual UI handlers (including a user-entered draft), not a live receiver.
        page.evaluate("""async () => {
            const {initAnalytics} = await import('./assets/site.mjs');
            window.fixtureEvents = [];
            await initAnalytics({transport:async (endpoint, payload) => {
                window.fixtureEvents.push(payload); return {ok:true};
            }});
        }""")
        panel.locator('[data-consent="reject"]').click()
        page.locator('[data-demo="architecture"]').click()
        page.keyboard.press("Escape")
        assert page.evaluate("window.fixtureEvents.length") == 0
        page.locator('#capabilities').scroll_into_view_if_needed()
        # Invoke the actual consent handler without Playwright scrolling back to the footer.
        assert page.locator('#ip-guard').evaluate("el => {const r=el.getBoundingClientRect();return Math.max(0,Math.min(innerHeight,r.bottom)-Math.max(0,r.top)) >= r.height*.5;}")
        panel.locator('[data-consent="accept"]').evaluate("el => el.click()")
        assert any(event['event'] == 'product_view' for event in page.evaluate('window.fixtureEvents'))
        page.locator('[data-demo="deep-blm"]').click()
        page.locator("#demo-intent").click()
        page.locator("#problem").fill(user_text)
        page.locator('#demand-form button[type="submit"]').click()
        page.locator("#draft-mailto").evaluate("el => el.addEventListener('click', e => e.preventDefault(), {once:true})")
        page.locator("#draft-mailto").click()
        page.keyboard.press("Escape")
        page.wait_for_function("document.querySelector('#demand-dialog').open === false")
        page.locator('#contact-a2a').click()
        assert page.locator('#demand-source').inner_text() == '来源：A2A 意向'
        page.keyboard.press('Escape')
        page.wait_for_function("window.fixtureEvents.some(e => e.event === 'intent_open' && e.category === 'a2a' && e.service === null) && window.fixtureEvents.some(e => e.event === 'mailto_click')")
        recorded = page.evaluate("window.fixtureEvents")
        assert any(event['event'] == 'intent_open' and event['category'] == 'a2a' and event['service'] is None for event in recorded)
        assert not any(event['event'] == 'a2a_interest' and event['surface'] == 'contact' for event in recorded)
        assert {"demo_open", "intent_open", "mail_draft_ready", "mailto_click"}.issubset({event["event"] for event in recorded})
        assert all(event['event'] != 'demo_complete' for event in recorded)
        allowed = {"event", "service", "category", "surface", "version", "audience", "is_test", "session_id", "event_id", "step"}
        assert all(set(event) <= allowed and event["is_test"] is True and event["audience"] == "browser_interaction" for event in recorded)
        assert user_text not in str(recorded) and "商业问题" not in str(recorded)
        panel.locator('[data-consent="reject"]').click()
        count = page.evaluate("window.fixtureEvents.length")
        page.locator('[data-demo="ip-guard"]').click()
        page.keyboard.press("Escape")
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
            protected.locator("[data-analytics] summary").click()
            assert "DNT/GPC" in protected.locator("footer [data-analytics]").inner_text()
            assert not protected.locator("footer [data-analytics-options]").is_visible()
            assert not protected.locator("[data-analytics-banner]").is_visible()
            protected.locator('[data-demo="ip-guard"]').click()
            protected.keyboard.press("Escape")
            assert requests == []
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
            for width in (320, 390, 820, 1440):
                page.set_viewport_size({"width": width, "height": 960})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (document, width)
                bounds = logo.bounding_box()
                header = page.locator(".site-header").bounding_box()
                assert bounds and header and bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= width
                assert bounds["y"] >= header["y"] and bounds["y"] + bounds["height"] <= header["y"] + header["height"]
                assert abs(bounds["width"] / bounds["height"] - 498 / 512) < 0.005, (document, width)
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
                check_official_brand(browser)
                print("PASS: official logo and favicon — all three pages, image decode, proportional sizing, 320/390/820/1440", flush=True)
                check_desktop(browser)
                print("PASS: desktop — four labelled dialogs, focus restoration, all A2A sample stages/reset/product changes", flush=True)
                check_mobile(browser)
                print("PASS: 320/390/820/1440 — no overflow, navigation, keyboard, reduced motion, unavailable storage, no-JS", flush=True)
                check_contact_paths(browser)
                print("PASS: demand sources, validation, safe mail drafts, clipboard fallback, consent/DNT/GPC fixtures; no real analytics transport", flush=True)
            finally:
                browser.close()
