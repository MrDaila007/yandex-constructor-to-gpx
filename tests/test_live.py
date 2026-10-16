"""Fetch public Constructor maps from Yandex. Fail if the HTML format changed."""

from __future__ import annotations

import os
import sys
import time
import unittest
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from fetch_usermap import fetch_html, normalize_map_url, parse_embedded_object  # noqa: E402
from gpx_lib import payloads_from_user_map  # noqa: E402

from tests.shape import FORMAT_HINT, assert_usermap_shape  # noqa: E402

CANARIES = [
    {
        "name": "nesvizh",
        "url": "https://yandex.com/maps/?um=constructor%3Afbd12684307cb322481c9e279ba4e3cd969a565ab626ec9ecb92fc2b36949e83&source=constructorLink",
        "min_files": 1,
        "min_wpt": 10,
        "min_trk": 50,
    },
    {
        "name": "bison-trail",
        "url": "https://yandex.com/maps/?um=constructor%3Aaf3b2c797a2526fe5b2a9971ff9e4886428b32275259e851d19a9b778c22fe48&source=constructorLink",
        "min_files": 3,
        "min_wpt": 1,
        "min_trk": 40,
    },
]


def _mirrors(url: str) -> list[str]:
    out = [url]
    if "yandex.com" in url:
        out.append(url.replace("yandex.com", "yandex.ru"))
    elif "yandex.ru" in url:
        out.append(url.replace("yandex.ru", "yandex.com"))
    return out


def fetch_live_usermap(url: str, attempts: int = 3) -> dict:
    last_fetch = None
    saw_html_without_usermap = False
    for candidate in _mirrors(url):
        target = normalize_map_url(candidate)
        for attempt in range(attempts):
            try:
                html = fetch_html(target, timeout=40)
            except (urllib.error.URLError, TimeoutError, OSError) as err:
                last_fetch = err
                time.sleep(2 * (attempt + 1))
                continue
            if "userMap" not in html and '"features"' not in html:
                saw_html_without_usermap = True
                last_fetch = ValueError("HTML has no userMap")
                continue
            try:
                return parse_embedded_object(html, "userMap")
            except ValueError as err:
                saw_html_without_usermap = True
                last_fetch = err
        time.sleep(1)
    if saw_html_without_usermap:
        raise AssertionError(f"{FORMAT_HINT} last={last_fetch}")
    raise AssertionError(
        f"Could not download Constructor HTML from Yandex ({last_fetch}). "
        "If this keeps happening, GitHub runners may be blocked — re-run the workflow."
    )


@unittest.skipIf(os.environ.get("YCG_SKIP_LIVE") == "1", "live Yandex fetch skipped")
class LiveConstructorFormatTests(unittest.TestCase):
    def test_canary_maps_still_export(self) -> None:
        for canary in CANARIES:
            with self.subTest(canary["name"]):
                data = fetch_live_usermap(canary["url"])
                assert_usermap_shape(data)
                payloads = payloads_from_user_map(data)
                self.assertGreaterEqual(
                    len(payloads),
                    canary["min_files"],
                    f"{canary['name']}: expected ≥{canary['min_files']} tracks, got {len(payloads)}",
                )
                for payload in payloads:
                    n_wpt = sum(1 for f in payload["features"] if f.get("type") == "placemark")
                    n_trk = len(payload["lineCoordinates"])
                    self.assertGreaterEqual(n_wpt, canary["min_wpt"], f"{canary['name']} waypoints")
                    self.assertGreaterEqual(n_trk, canary["min_trk"], f"{canary['name']} track points")


if __name__ == "__main__":
    unittest.main()
