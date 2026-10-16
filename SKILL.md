---
name: yandex-constructor-to-gpx
description: >-
  Converts a public Yandex Maps Constructor map (um=constructor:...) to GPX 1.1:
  one track per line plus waypoints. Use when the user gives a yandex.ru/maps or
  yandex.com/maps constructor link, asks for GPX/KML from Map Constructor, or
  wants OCR/trail course export with start/finish/obstacles. Handles several
  distances on one map (3K/5K/10K).
---

# Яндекс Конструктор → GPX

Официального API экспорта нет. Публичная страница карты уже содержит JSON `userMap` в HTML — этого достаточно, браузер не нужен.

Веб для пользователя: https://mrdaila007.github.io/yandex-constructor-to-gpx/ — ссылка, drop HTML или букмарклет **Яндекс → GPX** (перетащить кнопку на панель закладок; имя закладки берётся из текста кнопки). Букмарклет самодостаточный: CSP Яндекса блокирует `github.io`. Подробности в README.

## Запуск

```bash
python3 ~/.cursor/skills/yandex-constructor-to-gpx/scripts/constructor_to_gpx.py \
  'https://yandex.com/maps/?um=constructor%3A<HEX>&source=constructorLink' \
  -o /path/to/outdir
```

Несколько линий на одной карте → несколько `.gpx` (`{prefix}-{3k,5k,10k}.gpx`). Одна линия и `-o file.gpx` → один файл.

Опции: `--prefix`, `--title`, `--track-name`, `--save-json /tmp/usermap.json`, `--chrome` (headless CDP, если HTML пустой).

Источник: URL, constructor id (64 hex), сохранённый HTML или JSON `userMap`.

## Как достать данные

1. `GET` публичный URL как есть (`yandex.com` / `yandex.ru`), User-Agent браузера.
2. В HTML найти `"userMap":{...}` (скобки с учётом строк) — объект с `title` и `features`.
3. Не ходить в `api-maps.yandex.ru/services/constructor/...`: часто 302 на `api-maps.yandex.pl`, который не резолвится.

| Поле | Где | Формат |
|------|-----|--------|
| Название карты | `userMap.title` | строка, напр. `Bison Trail 18.10.2026` |
| Метки | `type: placemark` | `coordinates: [lon, lat]`; имя — `subtitle`, если это Старт/Финиш/Питьевой пункт (`title` бывает `S`/`F`) |
| Треки | `type: line` | `geometry.type: LineString`, `geometry.coordinates: [[lon,lat], ...]` |

Каждая линия → отдельный GPX. Метки общие, копируются во все файлы. Точки линии без прореживания. В GPX писать **lat, lon**.

## Waypoints

1. **Старт**, **Финиш**, **Питьевой пункт** — без номера.
2. Остальные placemark (порядок сайдбара, сверху вниз): для индекса `i`, если `i >= 3`, номер = `count - i`, имя `"<номер> <title>"`.
3. Порядок в GPX: Старт → Финиш → Питьевой пункт → препятствия 1…N.

## Если `userMap` нет в HTML

1. Повторить скрипт с `--chrome` (нужен `google-chrome` / chromium).
2. Либо открыть карту в cursor-ide-browser, дождаться `.user-maps-features-view`, снять `userMap`/`features` через CDP `Runtime.evaluate` — скрипт извлечения в `scripts/fetch_map.py` (`EXTRACT_JS`).
3. Ручной путь: Конструктор → Экспорт → GPX.

Не закрывать cookie-баннер: он не мешает.

## Проверка

- Столько GPX, сколько линий; длина трека haversine примерно совпадает с подписью (3K/5K/10K).
- Waypoints: все placemark карты (OCR-карта ≈ 23, Bison Trail — 3).
- Примеры: `~/Downloads/nesvizh-2026.gpx`; `~/Documents/bison-trail-2026-{3k,5k,10k}.gpx`.
