"""Offline regression tests on saved Constructor userMap dumps."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(SCRIPTS))

from fetch_usermap import parse_embedded_object  # noqa: E402
from gpx_lib import export_user_map, haversine_km, payloads_from_user_map  # noqa: E402

from tests.shape import assert_usermap_shape  # noqa: E402


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FixtureExportTests(unittest.TestCase):
    def test_nesvizh_shape_and_gpx(self) -> None:
        raw = _load("nesvizh.json")
        assert_usermap_shape(raw)
        self.assertEqual(raw["title"], "Несвиж 2026")
        payloads = payloads_from_user_map(raw)
        self.assertEqual(len(payloads), 1)
        pay = payloads[0]
        n_wpt = sum(1 for f in pay["features"] if f.get("type") == "placemark")
        self.assertEqual(n_wpt, 23)
        self.assertEqual(len(pay["lineCoordinates"]), 135)
        with tempfile.TemporaryDirectory() as tmp:
            written = export_user_map(raw, Path(tmp) / "nesvizh.gpx")
            self.assertEqual(len(written), 1)
            path, _title, wpt, trk, km = written[0]
            self.assertTrue(path.exists())
            self.assertEqual((wpt, trk), (23, 135))
            self.assertAlmostEqual(km, 4.92, places=1)
            xml = path.read_text(encoding="utf-8")
            self.assertIn("<gpx", xml)
            self.assertIn("<trkpt", xml)
            self.assertIn("Старт", xml)

    def test_bison_three_distances(self) -> None:
        raw = _load("bison-trail.json")
        assert_usermap_shape(raw)
        payloads = payloads_from_user_map(raw)
        self.assertEqual([p["lineTitle"] for p in payloads], ["3K", "5K", "10K"])
        kms = [round(haversine_km(p["lineCoordinates"]), 2) for p in payloads]
        self.assertEqual(kms, [3.28, 5.14, 10.23])
        with tempfile.TemporaryDirectory() as tmp:
            written = export_user_map(raw, Path(tmp), prefix="bison-trail-2026")
        self.assertEqual(len(written), 3)
        names = [p.name for p, *_ in written]
        self.assertEqual(names, ["bison-trail-2026-3k.gpx", "bison-trail-2026-5k.gpx", "bison-trail-2026-10k.gpx"])

    def test_html_userMap_scrape(self) -> None:
        raw = _load("nesvizh.json")
        html = '<!doctype html><html><script>app={"userMap":' + json.dumps(raw, ensure_ascii=False) + "}</script></html>"
        parsed = parse_embedded_object(html, "userMap")
        self.assertEqual(len(payloads_from_user_map(parsed)), 1)

    def test_missing_userMap_is_a_format_error(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_embedded_object("<html>no map here</html>", "userMap")
        self.assertIn("userMap", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
