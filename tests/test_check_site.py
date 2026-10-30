"""Exercise the checker against real files, without external services."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.check_site import check_site


VALID_HTML = """<!doctype html><html lang="zh-CN"><head>
<meta charset="UTF-8"><meta name="description" content="测试站点">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>测试站点</title><link rel="icon" href="data:image/svg+xml,%3Csvg/%3E">
</head><body><main id="main"><h1>站点</h1>
<a href="#main">正文</a><a href="mailto:hello@example.com">邮件</a>
<a href="https://external.invalid/page#unknown">外链</a>
<a href="http://external.invalid/">普通 HTTP 链接</a>
<img src="https://external.invalid/image.png" alt="">
</main></body></html>"""
SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_site.py"
VALID_SPA = '''<!doctype html><html lang="zh-CN"><head>
<meta charset="UTF-8"><meta name="description" content="HTML slide editor">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Source Slide Editor</title>
<script type="module" src="./assets/index-test123.js"></script>
<link rel="stylesheet" href="./assets/index-test123.css">
</head><body><div id="app"></div></body></html>'''


class CheckSiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write("CNAME", "www.deeparchi.com.cn\n")
        self.write("index.html", VALID_HTML)

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def with_body(self, content):
        self.write("index.html", VALID_HTML.replace("</main>", content + "</main>"))

    def test_valid_site_and_local_targets(self):
        self.write("about/index.html", VALID_HTML)
        self.write("assets/a b.svg", '<svg><path id="mark"/></svg>')
        self.write("assets/style.css", '@import "extra.css"; body { background: url("a%20b.svg#mark"); }')
        self.write("assets/extra.css", "/* url(missing.png) */ body { color: black; }")
        self.with_body('''<a href="about/?x=1#main">相对目录</a>
            <a href="/about/index.html#main">根路径</a>
            <a href="https://deeparchi.com.cn/about/#main">同站绝对链接</a>
            <a href="https://www.deeparchi.com.cn/#main">主域链接</a>
            <link rel="stylesheet" href="assets/style.css">
            <img src="assets/a%20b.svg#mark" srcset="assets/a%20b.svg 1x, assets/a%20b.svg 2x">
            <a href="#%6dain">编码 fragment</a>''')
        self.assertEqual(check_site(self.root), [])

    def test_required_metadata_and_structure(self):
        mutations = {
            "lang": ('lang="zh-CN"', ""),
            "title": ("<title>测试站点</title>", "<title> </title>"),
            "description": ('name="description"', 'name="other"'),
            "viewport": ('name="viewport"', 'name="other"'),
            "charset": ('charset="UTF-8"', 'charset="GBK"'),
            "h1": ("<h1>站点</h1>", "<h1>一</h1><h1>二</h1>"),
            "main": ('<main id="main">', '<div id="main">'),
        }
        for expected, (before, after) in mutations.items():
            with self.subTest(expected=expected):
                self.write("index.html", VALID_HTML.replace(before, after))
                self.assertTrue(any(expected in error for error in check_site(self.root)))

    def test_invalid_utf8(self):
        (self.root / "index.html").write_bytes(b"\xff")
        self.assertTrue(any("cannot parse UTF-8" in error for error in check_site(self.root)))

    def test_duplicate_ids(self):
        self.with_body('<div id="main"></div>')
        self.assertTrue(any("duplicate id: main" in error for error in check_site(self.root)))

    def test_missing_links_resources_and_fragments(self):
        self.write("about.html", VALID_HTML)
        for link, expected in (
            ('<a href="#absent">坏锚点</a>', "missing fragment"),
            ('<a href="about.html#absent">坏目标锚点</a>', "missing fragment"),
            ('<a href="missing.html">坏链接</a>', "missing local target"),
            ('<img src="missing.png">', "missing local target"),
            ('<source srcset="missing.png 1x, missing2.png 2x">', "missing local target"),
            ('<a href="https://deeparchi.com.cn/absent.html">同站坏链接</a>', "missing local target"),
        ):
            with self.subTest(link=link):
                self.with_body(link)
                self.assertTrue(any(expected in error for error in check_site(self.root)))

    def test_linked_html_is_checked(self):
        self.write("about.html", VALID_HTML.replace("#main", "#absent"))
        self.with_body('<a href="about.html">关于</a>')
        self.assertTrue(any("about.html: missing fragment" in error for error in check_site(self.root)))

    def known_spa(self, content=VALID_SPA):
        self.write("apps/source-slide-editor/index.html", content)
        self.write("apps/source-slide-editor/assets/index-test123.js", "document.querySelector('#app');")
        self.write("apps/source-slide-editor/assets/index-test123.css", "body {color:black}")
        self.with_body('<a href="apps/source-slide-editor/">Editor</a>')

    def test_known_spa_with_local_assets(self):
        self.known_spa()
        self.assertEqual(check_site(self.root), [])

    def test_known_spa_requires_mount_and_module(self):
        for before, after in (
            ('<div id="app"></div>', ''),
            ('<div id="app"></div>', '<main id="app"></main>'),
            ('<div id="app"></div>', '<div id="app"></div><div id="app"></div>'),
            ('type="module"', 'type="text/javascript"'),
            ('./assets/index-test123.js', 'https://external.invalid/index-test123.js'),
            ('<head>', '<head><base href="/">'),
        ):
            with self.subTest(before=before, after=after):
                self.known_spa(VALID_SPA.replace(before, after))
                errors = check_site(self.root)
                self.assertTrue(any("invalid known SPA" in e for e in errors), errors)
                self.assertTrue(any("expected one h1" in e for e in errors), errors)

    def test_known_spa_requires_existing_module_and_stylesheet(self):
        for asset in ("index-test123.js", "index-test123.css"):
            with self.subTest(asset=asset):
                self.known_spa()
                (self.root / "apps/source-slide-editor/assets" / asset).unlink()
                errors = check_site(self.root)
                self.assertTrue(any("invalid known SPA" in e for e in errors), errors)
                self.assertTrue(any("missing local target" in e for e in errors), errors)

    def test_known_spa_still_requires_metadata_and_safe_resources(self):
        for before, after, expected in (
            ('lang="zh-CN"', '', 'missing html lang'),
            ('<title>Source Slide Editor</title>', '<title> </title>', 'empty title'),
            ('charset="UTF-8"', 'charset="GBK"', 'UTF-8 charset'),
            ('name="description"', 'name="other"', 'missing meta description'),
            ('name="viewport"', 'name="other"', 'missing meta viewport'),
            ('</body>', '<img src="missing.png"></body>', 'missing local target'),
            ('</body>', '<script src="http://external.invalid/a.js"></script></body>', 'HTTP embedded'),
            ('</body>', '<img src="/%2e%2e/escape.png"></body>', 'leaves site root'),
        ):
            with self.subTest(expected=expected):
                self.known_spa(VALID_SPA.replace(before, after))
                self.assertTrue(any(expected in e for e in check_site(self.root)))

    def test_arbitrary_spa_and_empty_pages_require_static_structure(self):
        for name, content in (("other.html", VALID_SPA), ("empty.html", ""),
                              ("apps/unregistered/index.html", VALID_SPA)):
            with self.subTest(name=name):
                self.write(name, content)
                self.with_body(f'<a href="{name}">Page</a>')
                errors = check_site(self.root)
                self.assertTrue(any(f"{name}: expected one h1" in e for e in errors), errors)
                self.assertTrue(any(f"{name}: expected one main" in e for e in errors), errors)

    def test_symlinks_cannot_leave_site_tree(self):
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside) / "index.html"
            external.write_text(VALID_HTML, encoding="utf-8")
            (self.root / "linked").mkdir()
            (self.root / "linked/index.html").symlink_to(external)
            self.with_body('<a href="linked/">Escape</a>')
            self.assertTrue(any("leaves site root" in e for e in check_site(self.root)))
            self.known_spa()
            module = self.root / "apps/source-slide-editor/assets/index-test123.js"
            module.unlink()
            module.symlink_to(external)
            errors = check_site(self.root)
            self.assertTrue(any("invalid known SPA" in e for e in errors), errors)
            self.assertTrue(any("leaves site root" in e for e in errors), errors)

    def test_http_embedded_resources(self):
        for embedded in (
            '<script src="http://external.invalid/a.js"></script>',
            '<img src="//external.invalid/a.png" style="background:url(http://external.invalid/bg.png)">',
            '<link rel="stylesheet" href="http://external.invalid/a.css">',
            '<style>@import "http://external.invalid/a.css";</style>',
            '<source srcset="https://external.invalid/a.png 1x, http://external.invalid/b.png 2x">',
            '<object data="http://external.invalid/a.svg"></object>',
        ):
            with self.subTest(embedded=embedded):
                self.with_body(embedded)
                self.assertTrue(any("HTTP embedded resource" in error for error in check_site(self.root)))
        self.write("style.css", "body {background:url(http://external.invalid/bg.png)}")
        self.with_body('<link rel="stylesheet" href="style.css">')
        self.assertTrue(any("style.css: HTTP embedded resource" in error for error in check_site(self.root)))

    def test_exact_cname(self):
        for value in ("deeparchi.com.cn", "www.deeparchi.com.cn\nother.invalid", " www.deeparchi.com.cn "):
            with self.subTest(value=value):
                self.write("CNAME", value)
                self.assertTrue(any("CNAME:" in error for error in check_site(self.root)))
        (self.root / "CNAME").unlink()
        self.assertTrue(any("CNAME:" in error for error in check_site(self.root)))

    def test_cli_exit_codes_and_messages(self):
        command = [sys.executable, str(SCRIPT), "--root", str(self.root)]
        success = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(success.returncode, 0, success.stderr)
        self.assertIn("PASS:", success.stdout)
        self.with_body('<a href="#absent">坏链接</a>')
        failure = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(failure.returncode, 1)
        self.assertIn("missing fragment", failure.stderr)
        self.assertNotIn("PASS:", failure.stdout)


if __name__ == "__main__":
    unittest.main()
