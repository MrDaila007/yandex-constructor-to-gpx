"""Fetch Yandex Map Constructor data via headless Chrome DevTools Protocol (stdlib only)."""

from __future__ import annotations

import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import time
import urllib.parse
import urllib.request
from typing import Any

EXTRACT_JS = r"""(() => {
  const toArr = (v) => {
    if (!v) return [];
    if (typeof v.values === 'function') return [...v.values()];
    return Object.values(v);
  };
  const graphicsLines = () => {
    const feats = window.yandex_map && window.yandex_map._featuresByDataSource;
    if (!feats) return [];
    return toArr(feats.get('defaultGraphics')).filter(
      (f) => f.geometry && f.geometry.type === 'LineString',
    );
  };
  const lineHasCoords = (f) => {
    const c = (f.geometry && f.geometry.coordinates) || f.coordinates;
    return Array.isArray(c) && Array.isArray(c[0]);
  };

  const root = document.querySelector('.user-maps-features-view');
  if (root) {
    const rk = Object.keys(root).find((k) => k.startsWith('__reactFiber'));
    let fiber = root[rk];
    for (let i = 0; i < 40 && fiber; i++) {
      const data = fiber.memoizedProps && fiber.memoizedProps.data;
      if (data && data.features) {
        let features = data.features;
        if (!features.some((f) => f.type === 'line' && lineHasCoords(f))) {
          const gl = graphicsLines();
          let gi = 0;
          features = features.map((f) => {
            if (f.type !== 'line' || !gl[gi]) return f;
            const line = gl[gi++];
            return Object.assign({}, f, { geometry: line.geometry });
          });
        }
        return { title: data.title, features };
      }
      fiber = fiber.return;
    }
  }

  const map = window.yandex_map;
  if (!map) return { error: 'map not ready' };
  const gl = graphicsLines();
  if (!gl.length) return { error: 'no line' };

  const markers = toArr(map._featuresByDataSource.get('defaultMarkers')).filter(
    (f) => f.geometry && f.geometry.type === 'Point',
  );
  const rows = document.body.innerText
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean);
  const names = [];
  for (let i = 0; i < rows.length; i++) {
    const row = rows[i];
    if (row === 'Пробки' || row.startsWith('Открыть')) break;
    if (/^\d+$/.test(row) && i + 1 < rows.length) {
      names.push(rows[i + 1]);
      i += 1;
    } else if (!/^\d+$/.test(row)) {
      names.push(row);
    }
  }
  if (names.length !== markers.length) {
    return { error: 'name count mismatch', names: names.length, markers: markers.length };
  }

  const features = markers.map((m, idx) => ({
    type: 'placemark',
    title: names[idx],
    coordinates: m.geometry.coordinates,
  }));
  gl.forEach((line, idx) => {
    features.push({
      type: 'line',
      title: gl.length === 1 ? 'track' : `track-${idx + 1}`,
      geometry: line.geometry,
    });
  });
  const titleEl = document.querySelector('h1');
  const title =
    titleEl && !/cookie|cookies|куки/i.test(titleEl.textContent || '')
      ? titleEl.textContent.trim()
      : 'Yandex map';
  return { title, features };
})()"""


class WebSocketClient:
    def __init__(self, url: str) -> None:
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 80
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query

        self.sock = socket.create_connection((host, port), timeout=120)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(req.encode())
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("WebSocket handshake failed")
            data += chunk
        if b" 101 " not in data.split(b"\r\n", 1)[0]:
            raise RuntimeError(f"WebSocket upgrade failed: {data[:200]!r}")

    def send_text(self, text: str) -> None:
        payload = text.encode("utf-8")
        header = bytearray()
        header.append(0x81)
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack(">H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack(">Q", length))
        mask = os.urandom(4)
        header.extend(mask)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(header + masked)

    def recv_text(self) -> str:
        while True:
            header = self._recv_exact(2)
            opcode = header[0] & 0x0F
            masked = header[1] & 0x80
            length = header[1] & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._recv_exact(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._recv_exact(8))[0]
            mask = self._recv_exact(4) if masked else None
            payload = self._recv_exact(length)
            if mask:
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            if opcode == 0x8:
                raise RuntimeError("WebSocket closed")
            if opcode == 0x1:
                return payload.decode("utf-8")

    def _recv_exact(self, n: int) -> bytes:
        buf = bytearray()
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise RuntimeError("WebSocket connection closed")
            buf.extend(chunk)
        return bytes(buf)

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass


def _find_chrome() -> str:
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        path = shutil.which(name)
        if path:
            return path
    raise RuntimeError("Chrome/Chromium not found in PATH")


def _http_json(url: str, method: str = "GET") -> Any:
    req = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def normalize_map_url(url_or_id: str) -> str:
    text = url_or_id.strip()
    if text.startswith("http://") or text.startswith("https://"):
        return text
    if "constructor:" in text:
        um = urllib.parse.quote(text if text.startswith("constructor:") else f"constructor:{text}")
        return f"https://yandex.ru/maps/?um={um}&source=constructorLink"
    if len(text) == 64 and all(c in "0123456789abcdef" for c in text.lower()):
        um = urllib.parse.quote(f"constructor:{text}")
        return f"https://yandex.ru/maps/?um={um}&source=constructorLink"
    raise ValueError("expected Yandex maps URL or constructor map id")


def widget_fetch_url(url_or_id: str) -> str:
    """Headless-friendly embed URL (full yandex.ru/maps often returns 'limited')."""
    url = normalize_map_url(url_or_id)
    parsed = urllib.parse.urlparse(url)
    um = urllib.parse.parse_qs(parsed.query).get("um", [None])[0]
    if not um:
        raise ValueError("URL has no um=constructor:... parameter")
    um_q = urllib.parse.quote(um, safe="")
    return (
        "https://yandex.ru/map-widget/v1/?lang=ru_RU&scroll=false"
        f"&source=constructor-api&um={um_q}"
    )


class ChromeCdpSession:
    def __init__(self, port: int = 9333) -> None:
        self.port = port
        self.proc: subprocess.Popen | None = None
        self.ws: WebSocketClient | None = None
        self._msg_id = 0

    def start(self) -> None:
        chrome = _find_chrome()
        self.proc = subprocess.Popen(
            [
                chrome,
                f"--remote-debugging-port={self.port}",
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--window-size=1280,900",
                "--lang=ru-RU",
                "--disable-blink-features=AutomationControlled",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(40):
            try:
                _http_json(f"http://127.0.0.1:{self.port}/json/version")
                return
            except OSError:
                time.sleep(0.25)
            except urllib.error.URLError:
                time.sleep(0.25)
        raise RuntimeError("Chrome remote debugging did not start")

    def stop(self) -> None:
        if self.ws:
            self.ws.close()
            self.ws = None
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None

    def open_map(self, url: str) -> None:
        targets = _http_json(f"http://127.0.0.1:{self.port}/json/list")
        page = next(t for t in targets if t.get("type") == "page")
        self.ws = WebSocketClient(page["webSocketDebuggerUrl"])
        self.call("Page.enable")
        self.call("Runtime.enable")
        self.call("Page.navigate", {"url": url})
        time.sleep(3.0)

    def call(self, method: str, params: dict | None = None) -> Any:
        if not self.ws:
            raise RuntimeError("CDP session not connected")
        self._msg_id += 1
        mid = self._msg_id
        self.ws.send_text(json.dumps({"id": mid, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(self.ws.recv_text())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(msg["error"])
                return msg.get("result")

    def evaluate(self, expression: str) -> Any:
        result = self.call(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": False},
        )
        if result.get("exceptionDetails"):
            raise RuntimeError(result["exceptionDetails"])
        return result.get("result", {}).get("value")

    def wait_for_map_data(self, timeout_s: float = 90.0) -> dict:
        deadline = time.time() + timeout_s
        last_error = "timeout"
        while time.time() < deadline:
            ready = self.evaluate("Boolean(window.yandex_map)")
            if ready:
                value = self.evaluate(EXTRACT_JS)
                if isinstance(value, dict) and not value.get("error"):
                    return value
                if isinstance(value, dict):
                    last_error = str(value.get("error"))
            else:
                last_error = "map not ready"
            time.sleep(1.5)
        raise RuntimeError(f"failed to read map data: {last_error}")


def fetch_constructor_payload(url_or_id: str, port: int = 9333) -> dict:
    url = widget_fetch_url(url_or_id)
    session = ChromeCdpSession(port=port)
    try:
        session.start()
        session.open_map(url)
        return session.wait_for_map_data()
    finally:
        session.stop()
