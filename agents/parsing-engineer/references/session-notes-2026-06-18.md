# Заметки сессии 18.06.2026 — Парсинг новых источников

## Что сделано
- Загружено WorldFood Moscow: 10,360 записей из `data/worldfood_moscow_2025.json` в Supabase
- Загружено flagma.kz: 548 записей из `data/flagma_kz.json` в Supabase
- Итого прирост: +11,908 записей (24,806 → 36,714)

## Критические открытия

### Структура таблицы raw_parsed_data
Реальные колонты: `id, name, country, city, address, phone, email, website, description, categories, source, source_year, raw_data, created_at`
**НЕТ**: `country_iso`, `is_cis`, `parsed_at`, `uploaded_at`

### PGRST102 — Разные ключи в батче
Supabase требует одинаковый набор ключей во всех объектах батча. Решение: нормализовать все записи к единому набору ключей с пустыми строками по умолчанию.

### PGRST204 — Несуществующие колонки
Попытка вставить `country_iso` вызывает ошибку. Проверять реальную структуру через `GET ?limit=1`.

### subprocess.run без text=True
`result.stdout` без `text=True` возвращает bytes, сравнение со строкой падает с TypeError.

### candy-factory.ru href формат
Сайт отдаёт полные URL (`https://candy-factory.ru/russia/region-name/`), не относительные.
Нужно: `urllib.parse.urlparse(href).path` для нормализации.

## Не доделано (лимит итераций)
- candy-factory.ru: скрипт исправлен (patch в candy_factory.py), но не перезапущен
- productcenter.ru: скрипт есть, данные пустые, не запускался
- PROGRESS.md не обновлён
