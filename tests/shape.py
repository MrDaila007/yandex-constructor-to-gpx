"""Shared assertions for Constructor userMap JSON. Fail here if Yandex changes the page format."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from gpx_lib import line_coordinates, payloads_from_user_map  # noqa: E402

FORMAT_HINT = (
    "Yandex Constructor HTML/JSON shape changed — userMap is missing or no longer "
    "has line features with lon/lat coordinates. Update fetch_usermap.py / gpx_lib.py."
)


def assert_usermap_shape(data: dict) -> None:
    if not isinstance(data, dict):
        raise AssertionError(f"{FORMAT_HINT} (not an object)")
    if "features" not in data or not isinstance(data["features"], list) or not data["features"]:
        raise AssertionError(f"{FORMAT_HINT} (no features[])")
    types = {feat.get("type") for feat in data["features"]}
    has_line = "line" in types or bool(data.get("lineCoordinates"))
    if not has_line:
        raise AssertionError(f"{FORMAT_HINT} (no type:line / LineString)")
    for feat in data["features"]:
        if feat.get("type") == "line":
            geom = feat.get("geometry") or {}
            if geom and geom.get("type") not in (None, "LineString"):
                raise AssertionError(f"{FORMAT_HINT} (line geometry.type={geom.get('type')!r})")
            coords = line_coordinates(feat)
            if not coords or len(coords) < 2:
                raise AssertionError(f"{FORMAT_HINT} (line has no coordinate pairs)")
            lon, lat = coords[0]
            if not (-180 <= float(lon) <= 180 and -90 <= float(lat) <= 90):
                raise AssertionError(f"{FORMAT_HINT} (line coords not lon,lat)")
        elif feat.get("type") == "placemark":
            coords = feat.get("coordinates")
            if not (isinstance(coords, list) and len(coords) >= 2):
                raise AssertionError(f"{FORMAT_HINT} (placemark missing [lon,lat])")
    payloads_from_user_map(data)
