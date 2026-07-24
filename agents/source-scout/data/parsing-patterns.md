# Парсинг выставок — рабочие паттерны (06.2026)

## ITE Group платформа (WorldFood Moscow и др.)

### Пагинация
Сайт использует `onclick="searchFilter(N)"` — НЕ URL параметры, НЕ infinite scroll.

```python
# Правильная пагинация:
for page_num in range(1, 15):
    cards = page.query_selector_all('.card')
    # ... парсинг ...
    
    # Next page — клик по номеру
    nxt = page_num + 1
    btn = page.query_selector(f'a.page-link >> text="{nxt}"')
    if not btn:
        btn = page.query_selector('a.page-link >> text="»"')
    if btn:
        btn.click()
        page.wait_for_timeout(3000)
        page.wait_for_selector('.card', timeout=10000)
    else:
        break
```

### Структура карточки
- Имя: `.card-title a` или `h5 a`
- Страна: `.card-text` (НЕ `.country`!)
- Стенд: `.card-subtitle`

## Агропродмаш
- Все данные в HTML (2MB), НЕ нужен Playwright
- `requests.get(url, timeout=300)` работает
- Таблица: `table#fresh-table tbody tr`

## UzFood / AgroWorld Uzbekistan
- Playwright обязателен (JS SPA)
- `select_option` вызывает execution context destroyed — заново запрашивать элементы

## ITECA KZ — СЛОМАНА (HTTP 500, подтверждено 06.2026)

## WorldFood Istanbul — НЕДОСТУПНА (выставка в декабре 2026)

## Supabase UPSERT
Использовать `uuid.uuid4()` для moysklad_id — НЕ hash-based ID!
