#!/usr/bin/env python3
"""Fetch Yandex Map Constructor `userMap` JSON from the public maps HTML page."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def normalize_map_url(url_or_id: str) -> str:
    text = url_or_id.strip()
    if text.startswith("http://") or text.startswith("https://"):
        return text
    if "constructor:" in text:
        um = text if text.startswith("constructor:") else f"constructor:{text}"
        return (
            "https://yandex.ru/maps/?mode=usermaps&source=constructorLink"
            f"&um={urllib.parse.quote(um, safe='')}"
        )
    if len(text) == 64 and all(c in "0123456789abcdef" for c in text.lower()):
        um = f"constructor:{text}"
        return (
            "https://yandex.ru/maps/?mode=usermaps&source=constructorLink"
            f"&um={urllib.parse.quote(um, safe='')}"
        )
    raise ValueError("expected Yandex maps URL or constructor map id")


def parse_embedded_object(html: str, key: str = "userMap") -> dict[str, Any]:
    needle = f'"{key}":'
    start_search = 0
    last_error: Exception | None = None
    while True:
        idx = html.find(needle, start_search)
        if idx < 0:
            break
        start = html.find("{", idx)
        if start < 0:
            break
        try:
            obj, _end = _raw_json_object(html, start)
            if obj.get("features"):
                return obj
            last_error = ValueError(f"{key} object has no features")
        except json.JSONDecodeError as exc:
            last_error = exc
        start_search = idx + len(needle)
    if last_error:
        raise ValueError(f"failed to parse {key}: {last_error}") from last_error
    raise ValueError(f"{key} JSON not found in HTML")


def _raw_json_object(text: str, start: int) -> tuple[dict[str, Any], int]:
    depth = 0
    in_str = False
    esc = False
    for i, ch in enumerate(text[start:], start):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                return json.loads(text[start:end]), end
    raise ValueError("unclosed JSON object")


def fetch_html(url: str, timeout: float = 30.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "ru,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_usermap(url_or_id: str, timeout: float = 30.0) -> dict[str, Any]:
    url = normalize_map_url(url_or_id)
    html = fetch_html(url, timeout=timeout)
    return parse_embedded_object(html, "userMap")
