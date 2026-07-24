# Проблемы парсинга (обновлено 06.06.2026)

## ITECA (reg.iteca.kz)
- **Статус**: HTTP 500 на ВСЕ выставки (06.2026)
- Ранее была SQL ошибка, теперь просто 500
- **Решение**: Ждать восстановления сервера

## ITE Group (WorldFood Moscow и др.)
- **Статус**: JS-SPA — `requests` получает пустой HTML
- **Решение**: Python Playwright (`sync_playwright`)
- **Проблема**: карточки загружаются через JS после рендеринга

## Агропродмаш (icatalog.expocentr.ru)
- **Статус**: РАБОТАЕТ через requests (06.2026)
- Все данные в HTML (2MB на страницу), bootstrap-table с клиентской пагинацией
- **Метод**: `requests.get(url, timeout=300)` + BeautifulSoup
- **Селектор**: `table#fresh-table tbody tr`

## Playwright
- **Python**: УСТАНОВЛЕН — `from playwright.sync_api import sync_playwright`
- **Node.js**: НЕ УСТАНОВЛЕН — модуль `playwright` не найден через `node`
- **Рекомендация**: использовать только Python Playwright

## Supabase: moysklad_id — это PK
- НЕ использовать `id` в запросах — такой колонки нет!
- PK = `moysklad_id` (text/integer)
- Для выборки: `.eq('moysklad_id', value)` — НЕ `.eq('id', value)`

## Supabase: ON CONFLICT DO UPDATE ошибка (06.2026)
- **Ошибка**: "ON CONFLICT DO UPDATE command cannot affect row"
- **Причина**: В одном батче (50 записей) есть дубликаты `moysklad_id`
- **Решение**: Использовать `uuid.uuid4()` для генерации `moysklad_id`
- **Не работает**: `Prefer: resolution=merge-duplicates` с дубликатами внутри батча

## parse_exhibitions_v2.py — УСТАРЕЛ
- **НЕ ИСПОЛЬЗОВАТЬ** этот скрипт
- Использует прокси (лимит 1000 символов)
- Неправильные URL для выставок
- Пишет напрямую в `clients`, минуя `temp_clients`

## UzFood / AgroWorld (Узбекистан) — мало данных (06.2026)
- uzprint.uz: только 10 компаний за 2024 год
- **Playwright ошибка**: "Execution context was destroyed" при навигации между годами
- Сайт очень мало участников из СНГ (Uzbekistan: 1, Russian Federation: 2, Belarus: 1)
- Основные участники: India (3), Austria (2), Germany (1)
- **Вывод**: Источник не приоритетный, мало целевых компаний

## WorldFood Moscow 2025 (ITE Group) (06.2026)
- JS-SPA, Playwright работает
- Пагинация: `?page=N`, 24 карточки/страница
- Селекторы: `.card` или `div[class*=card]`
- Данные: Company name, Country в карточке

## ITECA (Казахстан) — по-прежнему сломана (06.2026)
- HTTP 500 на все выставки
- ExhCode формат: `FoodExpo%20Qazaqstan%202025` (не `foodexpo` как раньше)
- Даже с правильным ExhCode — сервер возвращает 500
