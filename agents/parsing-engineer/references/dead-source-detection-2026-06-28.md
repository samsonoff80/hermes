# Dead Source Detection — 27.06.2027

## Проблема

`parse_catalogs.py` содержал 5 парсеров (bozor.tj, inform.kg, georgiayp.com, madeinuzbekistan.ru, n4.biz). Все 5 источников оказались мёртвыми или нерелевантными:
- `bozor.tj` — "Site under construction", 0 компаний
- `inform.kg` — гороскоп/погода, не бизнес-каталог
- `georgiayp.com` — 404 на food-industry
- `madeinuzbekistan.ru` — Tilda SPA, нужен Playwright
- `n4.biz` — нет ссылок / SPA

Файл был удалён целиком. Потеряно было 0 данных т.к. ни один из источников ничего не давал.

## Правило: Проверяй источник ДО написания/поддержки парсера

**Перед каждым новым парсером:**
```bash
# Быстрая проверка что сайт живой и содержит данные
curl -s -o /dev/null -w "%{http_code}" --max-time 10 <url>
curl -s --max-time 10 <url> | head -c 500
```

**Красные флаги:**
- HTTP 4xx/5xx
- "Site under construction" / "Coming soon"
- Контент < 2KB (редирект, защита)
- Контент не содержит категорий/названий компаний
- SPA с пустым HTML (только `<script>` теги)

**Если источник мёртв — НЕ пиши парсер.** Вместо этого обнови `PROGRESS.md` с пометкой `❌ МЁРТВЫЙ`.

## Проверенные и мёртвые источники (27-29.06.2026)

| Источник | Статус | Причина |
|----------|--------|---------|
| bozor.tj | ❌ | Site under construction |
| inform.kg | ❌ | Гороскоп, не бизнес |
| georgiayp.com | ❌ | 404 на food-industry |
| madeinuzbekistan.ru | ❌ | Tilda SPA |
| n4.biz | ❌ | Нет данных |
| foodmarkets.ru | ❌ | Каталог требует регистрацию |
| yellowpages.uz | ❌ | Рубрики открыты, компании — регистрация |
| areg.am | ❌ | JS-render, нет пищевых категорий |
| pirexpo.ru | ❌ | Таймауты DNS |
| modernbakery.ru | ❌ | Таймауты DNS |
| ingredientsrussia.com | ❌ | DNS не резолвится |
| foodex.ru | ❌ | SSL certificate error |
| api-fns.ru | ❌ | Недоступен |
| 2gis.ru | ⚠️ | Нужен API-ключ |
| sostav.ru | ⚠️ | Только главная |
| b2b-center.ru | ❌ | HTTP 403/404 |
| katalog.kz | ❌ | DNS не резолвится |
| agroprodmash-expo.ru/catalog | ❌ | HTTP 404 (PDF скачаны с /doc_YYYY/) |
| world-food.ru | ⚠️ | Только главная, без каталога |

**parse_catalogs.py удалён** — не добавлять новые парсеры без предварительной проверки!
