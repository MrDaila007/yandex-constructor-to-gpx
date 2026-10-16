# yandex-constructor-to-gpx

Конвертирует публичную карту [Яндекс Конструктора](https://yandex.ru/map-constructor) (`um=constructor:...`) в GPX 1.1: трек по каждой линии и waypoints по меткам.

**Веб (GitHub Pages):** https://mrdaila007.github.io/yandex-constructor-to-gpx/

На странице можно вставить ссылку, перетащить сохранённый HTML карты или перетащить букмарклет на панель закладок и нажать его, стоя на странице Яндекс.Карт (так надёжнее: браузер не даёт GitHub Pages напрямую читать Яндекс).

Официального API экспорта нет. Скрипт качает публичную HTML-страницу и читает встроенный JSON `userMap`. Браузер и ключ API не нужны. Несколько дистанций на одной карте (3K / 5K / 10K) → несколько `.gpx`.

## Установка

Нужен Python 3.10+ (только стандартная библиотека).

```bash
git clone git@github.com:MrDaila007/yandex-constructor-to-gpx.git
cd yandex-constructor-to-gpx
ln -sf "$(pwd)/scripts/constructor_to_gpx.py" ~/.local/bin/yandex-constructor-gpx
```

Для Cursor-скилла клонируйте (или сделайте symlink) в `~/.cursor/skills/yandex-constructor-to-gpx`.

## Использование

```bash
yandex-constructor-gpx 'https://yandex.com/maps/?um=constructor%3A...' -o ./gpx

# одна трасса → один файл
yandex-constructor-gpx 'ССЫЛКА' -o ~/Downloads/route.gpx

# несколько линий → prefix-3k.gpx, prefix-5k.gpx, ...
yandex-constructor-gpx 'ССЫЛКА' -o ~/Documents --prefix bison-trail-2026

# сырой JSON карты
yandex-constructor-gpx 'ССЫЛКА' -o ./out --save-json ./usermap.json
```

Источник: URL `yandex.ru` / `yandex.com`, constructor id (64 hex), сохранённый HTML или JSON.

`--chrome` — запасной путь через headless Chrome, если в HTML нет `userMap`.

## Данные

| Что | Откуда | Координаты |
|-----|--------|------------|
| Название карты | `userMap.title` | |
| Метки | `type: placemark` | `[lon, lat]` |
| Треки | `type: line` → `LineString` | `[lon, lat]` |

В GPX пишется `lat, lon`. Имена **Старт / Финиш / Питьевой пункт** без номера (у Старт/Финиш имя может быть в `subtitle`, а `title` — `S`/`F`). Остальные метки нумеруются как в сайдбаре конструктора.

## Проверено

- [Несвиж 2026](https://yandex.com/maps/?um=constructor%3Afbd12684307cb322481c9e279ba4e3cd969a565ab626ec9ecb92fc2b36949e83) — 23 waypoint, 135 точек трека
- [Bison Trail 18.10.2026](https://yandex.com/maps/?um=constructor%3Aaf3b2c797a2526fe5b2a9971ff9e4886428b32275259e851d19a9b778c22fe48) — 3K / 5K / 10K
