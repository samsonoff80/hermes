# Справочник выставок

## ITECA платформа (reg.iteca.kz)

Базовый URL: `https://reg.iteca.kz/list/exponent/auth_s.aspx?ExhCode=<код>`

### Известные выставки

| Выставка | ExhCode | Страна | Года | Компаний |
|----------|---------|--------|------|----------|
| FoodExpo Qazaqstan | foodexpo | KZ | 2023-2025 | ~400/год |
| InterFood Astana | interfood | KZ | 2023-2025 | ~200/год |
| Horex Qazaqstan | horex | KZ | 2023-2025 | ~150/год |
| Agroworld Qazaqstan | agroworld | KZ | 2023-2025 | ~100/год |

**⚠️ СТАТУС: СЛОМАНА (HTTP 500, подтверждено 06.2026)**

## Агропродмаш (Россия)

URL: `https://icatalog.expocentr.ru/ru/exhibitions/<uuid>/list`

### UUID по годам
| Год | UUID | Компаний |
|-----|------|----------|
| 2023 | ac7d68bf-c129-11eb-80cc-a0d3c1fab97f | 844 |
| 2024 | 348532b3-e716-11ec-80cd-a0d3c1fab97f | 920 |
| 2025 | b67ac0af-40d1-11ee-80ce-a0d3c1fab97f | 856 |

**Метод**: requests напрямую (timeout=300), НЕ Playwright

## ITE Group (WorldFood и др.)

URL: `https://exhibitors-itegroup.exhibitoronlinemanual.com/<exhibition>/ru/Exhibitor`

### Известные выставки
| Выставка | URL | Компаний | Метод |
|----------|-----|----------|-------|
| WorldFood Moscow 2025 | worldfood-moscow-2025 | ~72 | Playwright + searchFilter |
| WorldFood Istanbul 2026 | worldfood-istanbul-2026 | — | Каталог ещё не доступен |

**Метод**: Playwright (JS-SPA). Пагинация через `onclick="searchFilter(N)"`.
Страна в `.card-text`, НЕ в `.country`.

## Продэкспо (Россия)

PDF-каталоги: Post Show Report на сайте prodexpo.ru

### Формат PDF-каталога
1. Продуктовый индекс: "НАЗВАНИЕ, СТРАНА\nСТРАНИЦА"
2. Алфавитный список: блоки с контактами+стендом
3. По залам: "НАЗВАНИЕ\nhttp://сайт\nСТЕНД"

## UzFood / AgroWorld Uzbekistan

URL: `https://uzprint.uz/en/exhibitors-list` (зеркало)

**Метод**: Playwright (JS SPA, select с годами → таблица)
**Данные**: колонки Company | Country | Stand № | Location

## Caspian AgroWeek (Азербайджан) — ✅ СПАРСЕН

URL: `https://caspianagroweek.az/ru/official-catalogue`

**Статус**: ✅ Спарсен (06.2026), 101 компания в temp_clients
**Метод**: Playwright → PDF viewer → PyMuPDF word coordinates
**Данные**: 178 компаний, 21 страна
**Структура PDF**: 124 стр (приветствия → алфавит → по странам → контакты → продуктовый индекс)

### Другие выставки на платформе ceo.az
- InterFood Azerbaijan (30-я, 2025)
- Caspian Agro (18-я, 2025)
- Архивные каталоги: ссылки на /mediafile/ пути
