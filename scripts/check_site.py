#!/usr/bin/env python3
"""Offline checks for the published HTML and its local links/resources."""

import argparse
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urljoin, urlsplit


EXPECTED_CNAME = "www.deeparchi.com.cn"
SITE_HOSTS = {EXPECTED_CNAME, "deeparchi.com.cn"}
RESOURCE_RELS = {"stylesheet", "icon", "preload", "modulepreload", "manifest"}
# This built Vue entry intentionally renders h1/main after its local module loads.
SPA_ENTRY = "apps/source-slide-editor/index.html"
CSS_URL = re.compile(
    r"url\(\s*['\"]?([^)'\"]+)['\"]?\s*\)|@import\s+['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)


def css_urls(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    return [first.strip() or second for first, second in CSS_URL.findall(css)]


class SiteHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = Counter()
        self.ids = Counter()
        self.lang = ""
        self.meta = {}
        self.charsets = []
        self.title = []
        self.references = []
        self.app_mounts = []
        self.module_sources = []
        self.stylesheets = []
        self.base = ""
        self._in_title = False
        self._in_style = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags[tag] += 1
        if attrs.get("id"):
            self.ids[attrs["id"]] += 1
        if attrs.get("id") == "app":
            self.app_mounts.append(tag)
        if tag == "script" and attrs.get("type") == "module":
            self.module_sources.append(attrs.get("src") or "")
        if tag == "link" and "stylesheet" in (attrs.get("rel") or "").split():
            self.stylesheets.append(attrs.get("href") or "")
        if tag == "html":
            self.lang = attrs.get("lang") or ""
        if tag == "meta":
            self.meta[(attrs.get("name") or "").lower()] = attrs.get("content") or ""
            if "charset" in attrs:
                self.charsets.append((attrs["charset"] or "").lower())
        if tag == "title":
            self._in_title = True
        if tag == "style":
            self._in_style = True
        if tag == "base" and not self.base:
            self.base = attrs.get("href") or ""
        if "href" in attrs and tag != "base":
            embedded = tag not in {"a", "area"} and (
                tag != "link" or bool(RESOURCE_RELS & set((attrs.get("rel") or "").lower().split()))
            )
            self.references.append((attrs["href"] or "", embedded))
        for name in ("src", "poster"):
            if name in attrs:
                self.references.append((attrs[name] or "", True))
        if tag == "object" and "data" in attrs:
            self.references.append((attrs["data"] or "", True))
        if "srcset" in attrs:
            for match in re.finditer(r"(?:^|,)\s*(data:[^\s]+|[^,\s]+)(?:\s+[^,]*)?", attrs["srcset"] or ""):
                self.references.append((match[1].rstrip(","), True))
        self.references.extend((url, True) for url in css_urls(attrs.get("style") or ""))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag == "style":
            self._in_style = False

    def handle_data(self, data):
        if self._in_title:
            self.title.append(data)
        if self._in_style:
            self.references.extend((url, True) for url in css_urls(data))


def check_site(root):
    root = Path(root).resolve()
    errors = []
    parsed = {}
    checked = set()

    def report(path, message):
        errors.append(f"{path.relative_to(root)}: {message}")

    def parse(path):
        if path in parsed:
            return parsed[path]
        document = SiteHTML()
        parsed[path] = document
        try:
            document.feed(path.read_text(encoding="utf-8"))
            document.close()
        except (OSError, UnicodeError, ValueError) as error:
            report(path, f"cannot parse UTF-8: {error}")
        return document

    def check_reference(source, base, raw, embedded):
        try:
            url = urlsplit(urljoin(base, raw.strip()))
        except ValueError as error:
            report(source, f"invalid URL {raw!r}: {error}")
            return
        if embedded and url.scheme == "http":
            report(source, f"HTTP embedded resource: {raw}")
        if url.scheme not in {"http", "https"} or url.hostname not in SITE_HOSTS:
            return  # data:, mailto:, and external URLs need no network access.
        target = (root / unquote(url.path).lstrip("/")).resolve()
        if not target.is_relative_to(root):
            report(source, f"link leaves site root: {raw}")
            return
        if target.is_dir():
            target = (target / "index.html").resolve()
            if not target.is_relative_to(root):
                report(source, f"link leaves site root: {raw}")
                return
        if not target.is_file():
            report(source, f"missing local target: {raw}")
            return
        if target.suffix.lower() in {".html", ".htm"}:
            check_html(target)
        elif target.suffix.lower() == ".css":
            check_css(target)
        if url.fragment:
            if target.suffix.lower() not in {".html", ".htm", ".svg"}:
                report(source, f"cannot resolve fragment in target: {raw}")
            elif unquote(url.fragment) not in parse(target).ids:
                report(source, f"missing fragment: {raw}")

    def document_url(path):
        return f"https://{EXPECTED_CNAME}/{path.relative_to(root).as_posix()}"

    def check_css(path):
        if path in checked:
            return
        checked.add(path)
        try:
            css = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            report(path, f"cannot read UTF-8 CSS: {error}")
            return
        for url in css_urls(css):
            check_reference(path, document_url(path), url, True)

    def check_html(path):
        if path in checked:
            return
        checked.add(path)
        html = parse(path)
        valid_spa = False
        if path.relative_to(root).as_posix() == SPA_ENTRY:
            def valid_asset(raw, extension):
                if not re.fullmatch(r"\./assets/index-[A-Za-z0-9_-]+\." + extension, raw):
                    return False
                asset = (path.parent / raw).resolve()
                return asset.is_relative_to(root) and asset.is_file()

            valid_spa = (
                not html.base and html.app_mounts == ["div"] and html.ids["app"] == 1
                and len(html.module_sources) == 1
                and valid_asset(html.module_sources[0], "js")
                and len(html.stylesheets) == 1
                and valid_asset(html.stylesheets[0], "css")
            )
            if not valid_spa:
                report(path, "invalid known SPA entry: requires div#app, no base, one existing local hashed module and stylesheet")
        for tag in (("html", "title") if valid_spa else ("html", "title", "h1", "main")):
            if html.tags[tag] != 1:
                report(path, f"expected one {tag}, found {html.tags[tag]}")
        if not html.lang.strip():
            report(path, "missing html lang")
        if not "".join(html.title).strip():
            report(path, "empty title")
        if html.charsets != ["utf-8"]:
            report(path, "expected one UTF-8 charset declaration")
        for name in ("description", "viewport"):
            if not html.meta.get(name, "").strip():
                report(path, f"missing meta {name}")
        for identifier, count in html.ids.items():
            if count > 1:
                report(path, f"duplicate id: {identifier}")
        base = urljoin(document_url(path), html.base)
        for url, embedded in html.references:
            check_reference(path, base, url, embedded)

    try:
        cname = (root / "CNAME").read_bytes()
        if cname not in {EXPECTED_CNAME.encode(), (EXPECTED_CNAME + "\n").encode(), (EXPECTED_CNAME + "\r\n").encode()}:
            report(root / "CNAME", f"expected only {EXPECTED_CNAME}")
    except OSError as error:
        report(root / "CNAME", str(error))
    check_html(root / "index.html")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = check_site(args.root)
    if errors:
        print("Site checks FAILED:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("PASS: HTML metadata/structure, IDs, local links/resources, HTTPS embeds and CNAME")
    return 0


if __name__ == "__main__":
    sys.exit(main())
