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


def check_contact_paths(browser):
    page = browser.new_page(viewport={"width": 1440, "height": 960}, reduced_motion="reduce")
    errors, failed_responses, failed_requests = page_errors(page)
    try:
        page.goto(BASE_URL, wait_until="networkidle")
        routes = [
            (".path-link", "讨论你的关键议题 →", "contact-consulting", "业务咨询", "场景与目标 ↗"),
            (".path-link", "发起合作对话 →", "contact-partnership", "合作洽谈", "能力与分工 ↗"),
            (".protocol-link", "申请 A2A 私测接入 →", "contact-a2a", "A2A 私测申请", "场景与接入边界 ↗"),
        ]

        def check_mailto(href, subject):
            url = urlsplit(href)
            assert url.scheme == "mailto" and url.path == "contact@deeparchi.com.cn"
            assert parse_qs(url.query) == {"subject": [subject]}
            assert not url.fragment

        assets = [
            ("Patent MCP", "已上线", "查看开源文档 ↗", "https://github.com/deeparchi-ai/patent-mcp-server"),
            ("SanctionsSight", "已上线", "预约演示 →", "DeepArchi｜SanctionsSight 演示预约"),
            ("认知外骨骼", "内测", "咨询内测 →", "DeepArchi｜认知外骨骼 内测咨询"),
            ("MACS", "开发中", "查看开源进展 ↗", "https://github.com/deeparchi-ai/macs"),
        ]
        cards = page.locator(".asset")
        assert cards.count() == len(assets)
        for index, (name, status, label, destination) in enumerate(assets):
            card = cards.nth(index)
            assert card.locator("h4").inner_text() == name
            assert card.locator(".status").inner_text() == status
            link = card.locator("a")
            assert link.count() == 1 and link.get_attribute("class") == "asset-link"
            assert link.inner_text() == label
            if destination.startswith("https:"):
                assert link.get_attribute("href") == destination
                assert link.get_attribute("target") == "_blank"
                assert set(link.get_attribute("rel").split()) == {"noopener", "noreferrer"}
            else:
                check_mailto(link.get_attribute("href"), destination)

        a2a = page.locator(".protocol").filter(has_text="A2A / PRIVATE PREVIEW")
        assert "当前以受控私测方式接入" in a2a.inner_text()
        assert "状态：私测 · 按场景与合作关系开放 · 不发布虚构服务地址" in a2a.inner_text()
        assert a2a.locator("a").count() == 1
        assert a2a.locator("a").get_attribute("href") == "#contact-a2a"

        for width in (320, 390, 820, 1440):
            page.set_viewport_size({"width": width, "height": 960 if width == 1440 else 844})
            for selector, inbound_label, anchor, label, guidance in routes:
                inbound = page.locator(selector).filter(has_text=inbound_label)
                assert inbound.get_attribute("href") == f"#{anchor}"
                inbound.click()
                page.wait_for_function("anchor => window.location.hash === '#' + anchor", arg=anchor)
                target = page.locator(f".contact-actions a#{anchor}")
                assert target.count() == 1 and target.is_visible()
                assert target.locator("span").all_text_contents() == [label, guidance]
                check_mailto(target.get_attribute("href"), f"DeepArchi｜{label}")
                page.wait_for_function(
                    """anchor => {
                        const link = document.getElementById(anchor);
                        const rect = link.getBoundingClientRect();
                        const header = document.querySelector('.site-header').getBoundingClientRect();
                        return link.matches(':target') && rect.top >= header.bottom && rect.bottom <= innerHeight;
                    }""",
                    arg=anchor,
                )
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), width
            for link in page.locator(".asset-link").all():
                assert link.bounding_box()["height"] >= 44
            assert not errors and not failed_responses and not failed_requests, {
                "console_errors": errors,
                "failed_responses": failed_responses,
                "failed_requests": failed_requests,
            }
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
                check_desktop(browser)
                print("PASS: desktop 1440x960 — hero, contact navigation, no horizontal overflow or page/resource errors", flush=True)
                check_mobile(browser)
                print("PASS: mobile 390x844 — menu open/close, capabilities navigation, no horizontal overflow or page/resource errors", flush=True)
                check_contact_paths(browser)
                print("PASS: contact paths at 320/390/820/1440 — fragment targets, email subjects, asset destinations, no horizontal overflow or page/resource errors", flush=True)
            finally:
                browser.close()
