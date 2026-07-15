from pathlib import Path
import os

from playwright.sync_api import sync_playwright


BASE_URL = "http://127.0.0.1:4173"
CHROME_PATH = os.environ.get(
    "CHROME_PATH", r"C:\Program Files\Google\Chrome\Application\chrome.exe"
)


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
    if not Path(CHROME_PATH).is_file():
        raise FileNotFoundError(f"Chrome executable not found: {CHROME_PATH}")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=CHROME_PATH, headless=True)
        try:
            check_desktop(browser)
            check_mobile(browser)
        finally:
            browser.close()
