# Яндекс Конструктор карт → GPX

<img src="docs/logo.png" width="88" height="88" alt="Конструктор → GPX">

[English](README.md) · **[Открыть веб-приложение](https://mrdaila007.github.io/yandex-constructor-to-gpx/?lang=ru)**

Экспорт публичной карты [Яндекс Конструктора](https://yandex.ru/map-constructor) (`um=constructor:…`) в **GPX 1.1**: трек по каждой линии и метки. Для трейлов, OCR, ориентирования, Garmin, Strava, Komoot и других GPS-приложений.

Официального экспорта GPX у опубликованных карт конструктора нет. Данные берутся из JSON `userMap`, который уже лежит в HTML публичной страницы. Несколько дистанций на одной карте (3K / 5K / 10K) → несколько `.gpx`.

[![CI](https://github.com/MrDaila007/yandex-constructor-to-gpx/actions/workflows/ci.yml/badge.svg)](https://github.com/MrDaila007/yandex-constructor-to-gpx/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-e27a2e.svg)](LICENSE)
[![Web](https://img.shields.io/badge/web-GitHub%20Pages-2f5d3a.svg)](https://mrdaila007.github.io/yandex-constructor-to-gpx/?lang=ru)

<p>
  <a href="https://mrdaila007.github.io/yandex-constructor-to-gpx/?lang=ru">
    <img src="docs/screenshot.png" alt="Сайт экспорта Яндекс Конструктора в GPX" width="920">
  </a>
</p>

Запросы вроде: яндекс конструктор карт gpx, экспорт трассы из конструктора, скачать трек Garmin, конструктор яндекс карты GPX Strava.

## Веб

**https://mrdaila007.github.io/yandex-constructor-to-gpx/** — русский и английский.

Три способа, от простого к надёжному.

### 1. Ссылка на карту

Вставь URL `yandex.com/maps` / `yandex.ru/maps` с `um=constructor:…` и нажми **Скачать GPX**.

Запрос идёт через публичный CORS-прокси: Яндекс не отдаёт карту напрямую со страницы GitHub Pages. Прокси иногда падает.

### 2. Файл HTML или JSON

На карте в браузере: Сохранить как → HTML. Перетащи файл на сайт. Либо JSON `userMap`, если он уже есть.

### 3. Букмарклет «Яндекс → GPX» (надёжнее)

CSP Яндекса блокирует скрипты с `github.io`, поэтому букмарклет **самодостаточный**: весь конвертер лежит в закладке.

1. Открой [страницу экспорта](https://mrdaila007.github.io/yandex-constructor-to-gpx/?lang=ru).
2. Перетащи кнопку **Яндекс → GPX** на панель закладок (имя закладки будет таким же).
3. Открой нужную карту конструктора в Яндексе.
4. Нажми закладку — скачаются `.gpx`.

Если браузер не даёт перетащить: на сайте нажми «скопировать javascript:», создай закладку вручную, имя `Яндекс → GPX`, в поле адреса вставь скопированное.

Кликать кнопку, оставаясь на GitHub Pages, бессмысленно: экспортировать можно только со страницы карты.

## CLI

Нужен Python 3.10+ (только стандартная библиотека).

```bash
git clone git@github.com:MrDaila007/yandex-constructor-to-gpx.git
cd yandex-constructor-to-gpx
ln -sf "$(pwd)/scripts/constructor_to_gpx.py" ~/.local/bin/yandex-constructor-gpx
```

Для Cursor-скилла: клон или symlink в `~/.cursor/skills/yandex-constructor-to-gpx`.

```bash
yandex-constructor-gpx 'https://yandex.com/maps/?um=constructor%3A...' -o ./gpx

# одна трасса → один файл
yandex-constructor-gpx 'ССЫЛКА' -o ~/Downloads/route.gpx

# несколько линий → prefix-3k.gpx, prefix-5k.gpx, ...
yandex-constructor-gpx 'ССЫЛКА' -o ~/Documents --prefix bison-trail-2026

# сырой JSON карты
yandex-constructor-gpx 'ССЫЛКА' -o ./out --save-json ./usermap.json
```

Источник: URL, constructor id (64 hex), сохранённый HTML или JSON.

`--chrome` — запасной путь через headless Chrome, если HTML пустой.

## Данные в GPX

| Что | Откуда | Координаты |
|-----|--------|------------|
| Название карты | `userMap.title` | |
| Метки | `type: placemark` | `[lon, lat]` |
| Треки | `type: line` → `LineString` | `[lon, lat]` |

В GPX пишется `lat, lon`. Имена **Старт / Финиш / Питьевой пункт** без номера (у Старт/Финиш имя может быть в `subtitle`, а `title` — `S`/`F`). Остальные метки нумеруются как в сайдбаре конструктора.

## Частые вопросы

**Работает с закрытыми картами?** Нет. Нужна публичная ссылка конструктора (`um=constructor:…`).

**Почему вставка ссылки иногда не срабатывает?** GitHub Pages не может скачать Яндекс напрямую (CORS). Сохрани карту как HTML или используй букмарклет.

**Можно загрузить в Garmin / Strava?** Да. GPX 1.1 с треком и метками — обычный формат для этих приложений.

**Это официальный инструмент Яндекса?** Нет. Читаются только данные, которые уже есть на публичной странице карты.

## Проверено

- [Несвиж 2026](https://yandex.com/maps/?um=constructor%3Afbd12684307cb322481c9e279ba4e3cd969a565ab626ec9ecb92fc2b36949e83) — 23 waypoint, 135 точек трека
- [Bison Trail 18.10.2026](https://yandex.com/maps/?um=constructor%3Aaf3b2c797a2526fe5b2a9971ff9e4886428b32275259e851d19a9b778c22fe48) — 3K / 5K / 10K

## CI

GitHub Actions на каждый push/PR и **каждый день в 06:17 UTC**.

- Фикстуры — известные карты Несвиж / Bison Trail по-прежнему собираются в GPX; JS совпадает с Python; букмарклет вшивается в сайт.
- Живые канарейки — скачивается HTML конструктора с Яндекса и парсится `userMap`. Если Яндекс сменит вёрстку и `userMap` пропадёт, упадёт job **Live Yandex page format**.

При падении по расписанию GitHub пишет на почту аккаунту, который последний менял `.github/workflows/ci.yml`. Вручную: Actions → CI → Run workflow.

## Лицензия

[MIT](LICENSE)
