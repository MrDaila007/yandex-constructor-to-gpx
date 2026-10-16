#!/usr/bin/env python3
"""Bake a self-contained javascript: bookmarklet into docs/index.html."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
CONVERT = ROOT / "docs" / "convert.js"
INDEX = ROOT / "docs" / "index.html"

RUNNER = """
try {
  var api = window.YandexConstructorGpx;
  var files = api.exportGpxFiles(api.parseEmbeddedObject(document.documentElement.outerHTML, "userMap"));
  api.downloadGpxFiles(files);
  alert("GPX: " + files.map(function (f) { return f.filename; }).join(", "));
} catch (err) {
  alert(err && err.message ? err.message : String(err));
}
"""

START = "<!--bookmarklet-src-start-->"
END = "<!--bookmarklet-src-end-->"


def bookmarklet_href() -> str:
    code = CONVERT.read_text(encoding="utf-8") + "\n" + RUNNER
    return "javascript:" + quote(code, safe="~!*()'")


def main() -> None:
    href = bookmarklet_href()
    html = INDEX.read_text(encoding="utf-8")
    block = f'{START}<script type="text/plain" id="bookmarklet-src">{href}</script>{END}'
    if START not in html or END not in html:
        raise SystemExit("index.html is missing bookmarklet markers")
    pre, rest = html.split(START, 1)
    _, post = rest.split(END, 1)
    INDEX.write_text(pre + block + post, encoding="utf-8")
    print(f"Wrote bookmarklet ({len(href)} chars)")


if __name__ == "__main__":
    main()
