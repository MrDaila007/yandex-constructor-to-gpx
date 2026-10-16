"""The baked javascript: bookmarklet must stay in docs/index.html."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BookmarkletBakeTests(unittest.TestCase):
    def test_index_contains_javascript_bookmarklet(self) -> None:
        subprocess.check_call([sys.executable, str(ROOT / "scripts" / "build_bookmarklet.py")], cwd=ROOT)
        html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        start = html.find('id="bookmarklet-src">')
        self.assertGreater(start, 0)
        href = html[start:].split(">", 1)[1].split("</script>", 1)[0]
        self.assertTrue(href.startswith("javascript:"))
        self.assertGreater(len(href), 10_000)
        self.assertIn("userMap", href)
        self.assertIn("YandexConstructorGpx", href)


if __name__ == "__main__":
    unittest.main()
