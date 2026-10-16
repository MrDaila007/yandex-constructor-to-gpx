#!/usr/bin/env python3
"""Yandex Map Constructor URL / HTML userMap JSON → one GPX per track."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

from fetch_usermap import fetch_usermap, normalize_map_url  # noqa: E402
from gpx_lib import export_user_map, load_user_map  # noqa: E402


def _chrome_fetch(source: str, port: int) -> dict:
    from fetch_map import fetch_constructor_payload
    payload = fetch_constructor_payload(source, port=port)
    if payload.get("features") and any(f.get("type") == "line" for f in payload["features"]):
        return payload
    features = list(payload.get("features") or [])
    coords = payload.get("lineCoordinates")
    if coords:
        features.append(
            {
                "type": "line",
                "title": payload.get("title") or "track",
                "geometry": {"type": "LineString", "coordinates": coords},
            }
        )
    return {
        "title": payload.get("title") or "Yandex map",
        "features": features,
        "lineCoordinates": coords,
    }


def _load_source(source: str, chrome: bool, cdp_port: int) -> dict:
    path = Path(source)
    if path.is_file() and path.suffix.lower() in {".json", ".html", ".htm"}:
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() in {".html", ".htm"}:
            from fetch_usermap import parse_embedded_object

            return parse_embedded_object(text, "userMap")
        return load_user_map(path)

    try:
        normalize_map_url(source)
    except ValueError:
        if path.is_file():
            return load_user_map(path)
        raise

    if chrome:
        return _chrome_fetch(source, cdp_port)

    try:
        return fetch_usermap(source)
    except Exception as html_exc:
        try:
            return _chrome_fetch(source, cdp_port)
        except Exception as chrome_exc:
            raise RuntimeError(
                f"HTML userMap failed ({html_exc}); Chrome fallback failed ({chrome_exc})"
            ) from chrome_exc


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a Yandex Map Constructor map to GPX (one file per line).",
        epilog=(
            "Examples:\n"
            "  constructor_to_gpx.py 'https://yandex.ru/maps/?um=constructor%3A...' -o ./gpx\n"
            "  constructor_to_gpx.py usermap.json -o route.gpx\n"
            "  constructor_to_gpx.py URL -o bison-trail-2026.gpx"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("source", help="Yandex maps URL, constructor id, JSON, or saved HTML")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output .gpx file or directory")
    parser.add_argument("--prefix", default=None, help="Filename prefix when writing several GPX files")
    parser.add_argument("--track-name", default=None, help="Override <trk><name> (default: line title)")
    parser.add_argument("--title", default=None, help="Override GPX metadata title")
    parser.add_argument("--save-json", type=Path, default=None, help="Also save parsed userMap JSON")
    parser.add_argument("--chrome", action="store_true", help="Fetch via headless Chrome CDP instead of HTML")
    parser.add_argument("--cdp-port", type=int, default=9333, help="Chrome remote debugging port")
    args = parser.parse_args()

    raw = _load_source(args.source, chrome=args.chrome, cdp_port=args.cdp_port)
    if args.save_json:
        args.save_json.parent.mkdir(parents=True, exist_ok=True)
        args.save_json.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved JSON to {args.save_json}", file=sys.stderr)

    written = export_user_map(
        raw,
        args.output,
        prefix=args.prefix,
        title=args.title,
        track_name=args.track_name,
    )
    for path, line_title, n_wpt, n_trk, km in written:
        print(f"Wrote {path} [{line_title}] ({n_wpt} waypoints, {n_trk} track points, ~{km:.2f} km)")


if __name__ == "__main__":
    main()
