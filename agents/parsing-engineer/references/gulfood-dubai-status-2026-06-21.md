# Gulfood Dubai 2026 — Статус парсинга (21.06.2026)

## Запуск
- **Дата**: 21.06.2026 06:00 (cron job)
- **Скрипт**: `scripts/parsers/gulfood_dubai.py`
- **Метод**: Playwright для cookies + urllib для AJAX пагинации
- **Статус**: Запущен в фоне (session_id: proc_50eb5af39dc5, pid: 78241)

## Ожидаемый результат
- ~3,255 компаний в секторе World Food
- 16 компаний/страницу, ~200+ страниц
- Поля: name, country, stand, detail_url, sector

## Что нужно сделать после завершения
1. Проверить `data/gulfood_dubai_2026.json` — сколько записей
2. Нормализовать записи к формату Supabase (name, country, city, address, phone, email, website, description, categories, source, source_year, raw_data)
3. Загрузить батчами по 50 в Supabase `raw_parsed_data`
4. Обновить PROGRESS.md

## Параметры AJAX (на будущее)
- **Endpoint**: `POST https://exhibitors.gulfood.com//Sectorlist/ajaxPaginationData/{page}` (ДВОЙНОЙ СЛЕШ!)
- **Body**: `page=N` (application/x-www-form-urlencoded)
- **Cookies**: AWSALB из начальной загрузки (получить через Playwright)
- **X-Requested-With**: XMLHttpRequest
- **Referer**: `https://exhibitors.gulfood.com/gulfood-2026/Sectorlist/world-food`
- **Селектор карточек**: `.item.mb-4` → `.exb-title` (название), `fa-map-marker` + span (стенд), `href` (detail_url)
