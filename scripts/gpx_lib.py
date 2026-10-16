#!/usr/bin/env python3
"""GPX builder for Yandex Map Constructor payloads (userMap HTML or CDP JSON)."""

from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

GPX_NS = "http://www.topografix.com/GPX/1/1"
SPECIAL_WPTS = frozenset({"Старт", "Финиш", "Питьевой пункт"})
_EARTH_KM = 6371.0088


def normalize_payload(raw: dict) -> dict:
    if isinstance(raw, dict) and "result" in raw and "value" in raw.get("result", {}):
        raw = raw["result"]["value"]
    if raw.get("error"):
        raise ValueError(f"export error: {raw['error']}")
    if "features" not in raw or "lineCoordinates" not in raw:
        raise ValueError("payload must contain features and lineCoordinates")
    return raw


def load_payload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_user_map(path: Path) -> dict:
    raw = load_payload(path)
    if isinstance(raw, dict) and "result" in raw and "value" in raw.get("result", {}):
        raw = raw["result"]["value"]
    if raw.get("error"):
        raise ValueError(f"export error: {raw['error']}")
    return raw


def placemark_display_name(feat: dict) -> str:
    title = (feat.get("title") or feat.get("caption") or "").strip()
    subtitle = (feat.get("subtitle") or "").strip()
    if subtitle in SPECIAL_WPTS:
        return subtitle
    if title in SPECIAL_WPTS:
        return title
    if title in {"S", "F", "Start", "Finish"} and subtitle:
        return subtitle
    return title or subtitle


def wpt_name(feat: dict, placemark_index: int, placemark_count: int) -> str:
    name = placemark_display_name(feat)
    if name in SPECIAL_WPTS or placemark_index < 3:
        return name or f"Point {placemark_index + 1}"
    num = placemark_count - placemark_index
    return f"{num} {name}"


def wpt_sort_key(name: str) -> tuple:
    if name == "Старт":
        return (0, 0)
    if name == "Финиш":
        return (0, 1)
    if name == "Питьевой пункт":
        return (0, 2)
    if name and name[0].isdigit():
        num = int(name.split(" ", 1)[0])
        return (1, num)
    return (2, name)


def line_coordinates(feat: dict) -> list | None:
    geom = feat.get("geometry") or {}
    coords = geom.get("coordinates") if isinstance(geom, dict) else None
    if coords is None:
        coords = feat.get("coordinates")
    if not coords or not isinstance(coords, list) or not isinstance(coords[0], list):
        return None
    return coords


def iter_lines(features: list[dict]):
    for feat in features:
        if feat.get("type") != "line":
            continue
        coords = line_coordinates(feat)
        if coords:
            yield feat, coords


def slugify(text: str, fallback: str = "route") -> str:
    text = (text or "").strip().lower().replace("ё", "е")
    text = re.sub(r"[.]+", "-", text)
    text = re.sub(r"[^a-z0-9а-я]+", "-", text, flags=re.I)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or fallback


def haversine_km(coords: list) -> float:
    dist = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        p1, p2 = math.radians(lat1), math.radians(lat2)
        dphi = p2 - p1
        dl = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        dist += 2 * _EARTH_KM * math.asin(math.sqrt(a))
    return dist


def payloads_from_user_map(raw: dict) -> list[dict]:
    if isinstance(raw, dict) and "result" in raw and "value" in raw.get("result", {}):
        raw = raw["result"]["value"]
    if raw.get("error"):
        raise ValueError(f"export error: {raw['error']}")

    features = raw.get("features")
    if not features:
        raise ValueError("userMap has no features")

    placemarks = [f for f in features if f.get("type") == "placemark"]
    lines = list(iter_lines(features))
    if not lines and raw.get("lineCoordinates"):
        lines = [({"title": raw.get("trackName") or "track"}, raw["lineCoordinates"])]
    if not lines:
        raise ValueError("userMap has no LineString tracks")

    map_title = (raw.get("title") or "Yandex map").strip()
    out = []
    for feat, coords in lines:
        line_title = (feat.get("title") or feat.get("caption") or "").strip() or "track"
        out.append(
            {
                "title": map_title,
                "lineTitle": line_title,
                "features": placemarks,
                "lineCoordinates": coords,
            }
        )
    return out


def build_gpx(payload: dict, track_name: str | None = None, title_override: str | None = None) -> ET.Element:
    payload = dict(payload)
    if "lineCoordinates" not in payload:
        raise ValueError("payload must contain lineCoordinates")
    title = title_override or payload.get("title") or "Yandex map"
    line_coords = payload["lineCoordinates"]
    placemarks = [f for f in payload.get("features", []) if f.get("type") == "placemark"]
    count = len(placemarks)
    trk_name = track_name or payload.get("lineTitle") or "track"

    gpx = ET.Element(
        "gpx",
        {"version": "1.1", "creator": "yandex-constructor-gpx", "xmlns": GPX_NS},
    )
    meta = ET.SubElement(gpx, "metadata")
    ET.SubElement(meta, "name").text = title
    ET.SubElement(meta, "desc").text = "Экспорт из Яндекс.Карт (конструктор)"

    wpts: list[tuple[tuple, str, float, float]] = []
    for idx, feat in enumerate(placemarks):
        lon, lat = feat["coordinates"]
        name = wpt_name(feat, idx, count)
        wpts.append((wpt_sort_key(name), name, lat, lon))
    wpts.sort(key=lambda x: x[0])

    for _, name, lat, lon in wpts:
        wpt = ET.SubElement(gpx, "wpt", {"lat": f"{lat:.8f}", "lon": f"{lon:.8f}"})
        ET.SubElement(wpt, "name").text = name

    trk = ET.SubElement(gpx, "trk")
    ET.SubElement(trk, "name").text = trk_name
    trkseg = ET.SubElement(trk, "trkseg")
    for lon, lat in line_coords:
        ET.SubElement(trkseg, "trkpt", {"lat": f"{lat:.8f}", "lon": f"{lon:.8f}"})

    return gpx


def write_gpx(gpx: ET.Element, out: Path) -> None:
    xml = ET.tostring(gpx, encoding="unicode")
    pretty = minidom.parseString(xml).toprettyxml(indent="  ", encoding="utf-8")
    lines = [ln for ln in pretty.decode("utf-8").splitlines() if ln.strip()]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def payload_to_gpx(
    payload: dict,
    out: Path,
    track_name: str | None = None,
    title: str | None = None,
) -> tuple[int, int]:
    if "lineCoordinates" not in payload and "features" in payload:
        payloads = payloads_from_user_map(payload)
        if len(payloads) != 1:
            raise ValueError("userMap has multiple lines; use export_user_map()")
        payload = payloads[0]
    else:
        payload = normalize_payload(payload)
    gpx = build_gpx(payload, track_name=track_name, title_override=title)
    write_gpx(gpx, out)
    n_wpt = sum(1 for f in payload["features"] if f.get("type") == "placemark")
    return n_wpt, len(payload["lineCoordinates"])


def output_path_for_line(out: Path, prefix: str, line_title: str, n_lines: int) -> Path:
    slug = slugify(line_title, fallback="track")
    if n_lines == 1 and out.suffix.lower() == ".gpx":
        return out
    if out.suffix.lower() == ".gpx":
        return out.with_name(f"{out.stem}-{slug}.gpx")
    return out / f"{prefix}-{slug}.gpx"


def export_user_map(
    raw: dict,
    out: Path,
    prefix: str | None = None,
    title: str | None = None,
    track_name: str | None = None,
) -> list[tuple[Path, str, int, int, float]]:
    payloads = payloads_from_user_map(raw)
    map_title = (raw.get("title") or "Yandex map").strip()
    prefix = prefix or slugify(map_title, fallback="yandex-map")
    n_lines = len(payloads)
    if n_lines == 1 and out.suffix.lower() != ".gpx":
        out.mkdir(parents=True, exist_ok=True)
    elif n_lines > 1 and out.suffix.lower() != ".gpx":
        out.mkdir(parents=True, exist_ok=True)

    written = []
    for payload in payloads:
        line_title = payload["lineTitle"]
        path = output_path_for_line(out, prefix, line_title, n_lines)
        meta_title = title or (f"{map_title} — {line_title}" if n_lines > 1 else map_title)
        n_wpt, n_trk = payload_to_gpx(
            payload,
            path,
            track_name=track_name or line_title,
            title=meta_title,
        )
        km = haversine_km(payload["lineCoordinates"])
        written.append((path, line_title, n_wpt, n_trk, km))
    return written
