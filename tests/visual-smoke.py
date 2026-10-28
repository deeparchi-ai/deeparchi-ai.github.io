from pathlib import Path
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from threading import Thread
from urllib.parse import urlsplit

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
    page.goto(BASE_URL, wait_until="networkidle")

    assert "AI 原生服务公司" in page.locator("#hero-title").inner_text()
    assert page.locator('a[href="#contact"]').count() >= 2
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")

    page.locator(".button-primary").click()
    page.wait_for_function("window.location.hash === '#contact'")
    assert page.locator("#contact-title").is_visible()
    assert not errors and not failed_responses and not failed_requests, {
        "console_errors": errors,
        "failed_responses": failed_responses,
        "failed_requests": failed_requests,
    }


def check_mobile(browser):
    page = browser.new_page(viewport={"width": 390, "height": 844})
    errors, failed_responses, failed_requests = page_errors(page)
    page.goto(BASE_URL, wait_until="networkidle")

    menu_button = page.locator(".menu-button")
    assert menu_button.get_attribute("aria-expanded") == "false"
    assert menu_button.get_attribute("aria-label") == "打开导航菜单"
    menu_button.click()
    assert menu_button.get_attribute("aria-expanded") == "true"
    assert menu_button.get_attribute("aria-label") == "关闭导航菜单"
    assert "open" in (page.locator("#nav-links").get_attribute("class") or "")

    page.get_by_role("link", name="能力", exact=True).click()
    page.wait_for_function("window.location.hash === '#capabilities'")
    assert menu_button.get_attribute("aria-expanded") == "false"
    assert "open" not in (page.locator("#nav-links").get_attribute("class") or "")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert not errors and not failed_responses and not failed_requests, {
        "console_errors": errors,
        "failed_responses": failed_responses,
        "failed_requests": failed_requests,
    }


if __name__ == "__main__":
    if CHROME_PATH is not None and not Path(CHROME_PATH).is_file():
        raise FileNotFoundError(f"CHROME_PATH is not a file: {CHROME_PATH!r}")

    with site_url() as BASE_URL:
        print(f"Testing {BASE_URL}", flush=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=CHROME_PATH, headless=True)
            try:
                check_desktop(browser)
                print("PASS: desktop 1440x960 — hero, contact navigation, no horizontal overflow or page/resource errors", flush=True)
                check_mobile(browser)
                print("PASS: mobile 390x844 — menu open/close, capabilities navigation, no horizontal overflow or page/resource errors", flush=True)
            finally:
                browser.close()
