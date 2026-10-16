(function (root) {
  const SPECIAL_WPTS = new Set(["Старт", "Финиш", "Питьевой пункт"]);
  const EARTH_KM = 6371.0088;
  const GPX_NS = "http://www.topografix.com/GPX/1/1";

  function normalizeMapUrl(urlOrId) {
    const text = (urlOrId || "").trim();
    if (!text) throw new Error("Вставь ссылку на карту конструктора");
    if (text.startsWith("http://") || text.startsWith("https://")) return text;
    if (text.includes("constructor:")) {
      const um = text.startsWith("constructor:") ? text : `constructor:${text}`;
      return `https://yandex.ru/maps/?mode=usermaps&source=constructorLink&um=${encodeURIComponent(um)}`;
    }
    if (/^[0-9a-f]{64}$/i.test(text)) {
      return `https://yandex.ru/maps/?mode=usermaps&source=constructorLink&um=${encodeURIComponent(`constructor:${text}`)}`;
    }
    throw new Error("Нужна ссылка yandex.ru/maps с um=constructor:... или id карты");
  }

  function rawJsonObject(text, start) {
    let depth = 0;
    let inStr = false;
    let esc = false;
    for (let i = start; i < text.length; i++) {
      const ch = text[i];
      if (inStr) {
        if (esc) esc = false;
        else if (ch === "\\") esc = true;
        else if (ch === '"') inStr = false;
        continue;
      }
      if (ch === '"') inStr = true;
      else if (ch === "{") depth += 1;
      else if (ch === "}") {
        depth -= 1;
        if (depth === 0) {
          const end = i + 1;
          return { obj: JSON.parse(text.slice(start, end)), end };
        }
      }
    }
    throw new Error("unclosed JSON object");
  }

  function parseEmbeddedObject(html, key) {
    key = key || "userMap";
    const needle = `"${key}":`;
    let startSearch = 0;
    let lastError = null;
    while (true) {
      const idx = html.indexOf(needle, startSearch);
      if (idx < 0) break;
      const start = html.indexOf("{", idx);
      if (start < 0) break;
      try {
        const { obj } = rawJsonObject(html, start);
        if (obj && obj.features) return obj;
        lastError = new Error(`${key} object has no features`);
      } catch (err) {
        lastError = err;
      }
      startSearch = idx + needle.length;
    }
    if (lastError) throw lastError;
    throw new Error("В HTML нет userMap — открой публичную ссылку конструктора");
  }

  function parseUserMap(raw) {
    if (raw && raw.result && raw.result.value) raw = raw.result.value;
    if (raw && raw.error) throw new Error(raw.error);
    if (!raw || !raw.features) throw new Error("userMap has no features");
    return raw;
  }

  function placemarkDisplayName(feat) {
    const title = String(feat.title || feat.caption || "").trim();
    const subtitle = String(feat.subtitle || "").trim();
    if (SPECIAL_WPTS.has(subtitle)) return subtitle;
    if (SPECIAL_WPTS.has(title)) return title;
    if (["S", "F", "Start", "Finish"].includes(title) && subtitle) return subtitle;
    return title || subtitle;
  }

  function wptName(feat, index, count) {
    const name = placemarkDisplayName(feat);
    if (SPECIAL_WPTS.has(name) || index < 3) return name || `Point ${index + 1}`;
    return `${count - index} ${name}`;
  }

  function wptSortKey(name) {
    if (name === "Старт") return [0, 0];
    if (name === "Финиш") return [0, 1];
    if (name === "Питьевой пункт") return [0, 2];
    if (name && /^\d/.test(name)) return [1, parseInt(name, 10)];
    return [2, name];
  }

  function lineCoordinates(feat) {
    const geom = feat.geometry || {};
    let coords = geom.coordinates;
    if (coords == null) coords = feat.coordinates;
    if (!Array.isArray(coords) || !Array.isArray(coords[0])) return null;
    return coords;
  }

  function slugify(text, fallback) {
    fallback = fallback || "route";
    let value = String(text || "")
      .trim()
      .toLowerCase()
      .replaceAll("ё", "е")
      .replace(/\.+/g, "-")
      .replace(/[^a-z0-9а-я]+/gi, "-")
      .replace(/-{2,}/g, "-")
      .replace(/^-|-$/g, "");
    return value || fallback;
  }

  function haversineKm(coords) {
    let dist = 0;
    for (let i = 1; i < coords.length; i++) {
      const [lon1, lat1] = coords[i - 1];
      const [lon2, lat2] = coords[i];
      const p1 = (lat1 * Math.PI) / 180;
      const p2 = (lat2 * Math.PI) / 180;
      const dphi = p2 - p1;
      const dl = ((lon2 - lon1) * Math.PI) / 180;
      const a =
        Math.sin(dphi / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
      dist += 2 * EARTH_KM * Math.asin(Math.sqrt(a));
    }
    return dist;
  }

  function payloadsFromUserMap(raw) {
    const data = parseUserMap(raw);
    const features = data.features;
    const placemarks = features.filter((f) => f.type === "placemark");
    let lines = features
      .filter((f) => f.type === "line")
      .map((feat) => ({ feat, coords: lineCoordinates(feat) }))
      .filter((row) => row.coords);
    if (!lines.length && data.lineCoordinates) {
      lines = [{ feat: { title: data.trackName || "track" }, coords: data.lineCoordinates }];
    }
    if (!lines.length) throw new Error("На карте нет линий маршрута");
    const mapTitle = String(data.title || "Yandex map").trim();
    return lines.map(({ feat, coords }) => ({
      title: mapTitle,
      lineTitle: String(feat.title || feat.caption || "").trim() || "track",
      features: placemarks,
      lineCoordinates: coords,
    }));
  }

  function xmlEscape(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fmt(n) {
    return Number(n).toFixed(8);
  }

  function buildGpx(payload, trackName, titleOverride) {
    const title = titleOverride || payload.title || "Yandex map";
    const coords = payload.lineCoordinates;
    const placemarks = (payload.features || []).filter((f) => f.type === "placemark");
    const trkName = trackName || payload.lineTitle || "track";
    const wpts = placemarks.map((feat, idx) => {
      const [lon, lat] = feat.coordinates;
      const name = wptName(feat, idx, placemarks.length);
      return { key: wptSortKey(name), name, lat, lon };
    });
    wpts.sort((a, b) => a.key[0] - b.key[0] || (a.key[1] < b.key[1] ? -1 : a.key[1] > b.key[1] ? 1 : 0));

    const wptXml = wpts
      .map(
        (w) =>
          `  <wpt lat="${fmt(w.lat)}" lon="${fmt(w.lon)}">\n    <name>${xmlEscape(w.name)}</name>\n  </wpt>`,
      )
      .join("\n");
    const trkXml = coords
      .map(([lon, lat]) => `      <trkpt lat="${fmt(lat)}" lon="${fmt(lon)}"/>`)
      .join("\n");

    return `<?xml version="1.0" encoding="utf-8"?>
<gpx xmlns="${GPX_NS}" version="1.1" creator="yandex-constructor-gpx">
  <metadata>
    <name>${xmlEscape(title)}</name>
    <desc>Экспорт из Яндекс.Карт (конструктор)</desc>
  </metadata>
${wptXml}
  <trk>
    <name>${xmlEscape(trkName)}</name>
    <trkseg>
${trkXml}
    </trkseg>
  </trk>
</gpx>
`;
  }

  function exportGpxFiles(raw) {
    const payloads = payloadsFromUserMap(raw);
    const mapTitle = String(raw.title || payloads[0].title || "Yandex map").trim();
    const prefix = slugify(mapTitle, "yandex-map");
    const n = payloads.length;
    return payloads.map((payload) => {
      const lineTitle = payload.lineTitle;
      const slug = slugify(lineTitle, "track");
      const filename = n === 1 ? `${prefix}.gpx` : `${prefix}-${slug}.gpx`;
      const metaTitle = n > 1 ? `${mapTitle} — ${lineTitle}` : mapTitle;
      const gpx = buildGpx(payload, lineTitle, metaTitle);
      return {
        filename,
        lineTitle,
        mapTitle: metaTitle,
        gpx,
        nWpt: payload.features.filter((f) => f.type === "placemark").length,
        nTrk: payload.lineCoordinates.length,
        km: haversineKm(payload.lineCoordinates),
      };
    });
  }

  function parseInputText(text) {
    const trimmed = text.trim();
    if (trimmed.startsWith("{")) return parseUserMap(JSON.parse(trimmed));
    return parseEmbeddedObject(text, "userMap");
  }

  async function fetchUserMapHtml(url) {
    const target = normalizeMapUrl(url);
    const proxies = [
      (u) => `https://api.allorigins.win/raw?url=${encodeURIComponent(u)}`,
      (u) => `https://api.allorigins.win/get?url=${encodeURIComponent(u)}`,
      (u) => `https://api.codetabs.com/v1/proxy?quest=${encodeURIComponent(u)}`,
    ];
    let lastErr = null;
    for (let attempt = 0; attempt < 2; attempt++) {
      for (const make of proxies) {
        try {
          const resp = await fetch(make(target));
          if (!resp.ok) {
            lastErr = new Error(`proxy HTTP ${resp.status}`);
            continue;
          }
          let html = await resp.text();
          if (html.trim().startsWith("{")) {
            try {
              const parsed = JSON.parse(html);
              if (parsed && typeof parsed.contents === "string") html = parsed.contents;
            } catch (_err) {
              /* not allorigins wrapper */
            }
          }
          if (!html.includes("userMap") && !html.includes('"features"')) {
            lastErr = new Error("proxy вернул страницу без userMap");
            continue;
          }
          return parseEmbeddedObject(html, "userMap");
        } catch (err) {
          lastErr = err;
        }
      }
    }
    throw lastErr || new Error("Не удалось скачать карту");
  }

  function downloadGpxFiles(files) {
    files.forEach((file, i) => {
      setTimeout(() => {
        const blob = new Blob([file.gpx], { type: "application/gpx+xml" });
        const href = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = href;
        a.download = file.filename;
        a.click();
        setTimeout(() => URL.revokeObjectURL(href), 1500);
      }, i * 250);
    });
  }

  root.YandexConstructorGpx = {
    normalizeMapUrl,
    parseEmbeddedObject,
    parseUserMap,
    parseInputText,
    exportGpxFiles,
    fetchUserMapHtml,
    downloadGpxFiles,
    slugify,
    haversineKm,
  };
})(typeof globalThis !== "undefined" ? globalThis : window);
