# Gulfood Dubai 2026 — Playwright + urllib метод (2026-06-20)

## Проблема
Прямой urllib POST к AJAX endpoint Gulfood не работает без cookies.
Proton Proxy возвращает 405 для POST.

## Решение
1. Playwright (локальный) → `context.cookies()` для получения AWSALB cookie
2. urllib.request с Cookie header для POST-запросов к AJAX endpoint

## Ключевые открытия

### URL с двойным слешем
- ❌ `/Sectorlist/ajaxPaginationData/0` → 404
- ✅ `//Sectorlist/ajaxPaginationData/0` → 200, 45KB данных

### Структура ответа AJAX
```html
<div class="item mb-4">
    <div class="thumbnail">
        <div class="row p-md-2">
            <div class="img-event col-sm-3 col-md-3 col-12 sm-mb-10 mb-3">
                <img src="...">
            </div>
            <div class="col-sm-6 col-md-6 col-12">
                <strong class="exb-title">
                    <a href="...ExbDetails/...">COMPANY NAME</a>
                </strong>
                <div class="card-text">Country</div>
                <i class="fa fa-map-marker"></i> <span>Stand Number</span>
            </div>
        </div>
    </div>
</div>
```

### Cookies
- AWSALB cookie необходим для POST-запросов
- Получается через `context.cookies()` после `page.goto(initial_url, wait_until='networkidle')`

### Селекторы
- Карточка: `.item.mb-4`
- Название: `.exb-title a`
- Ссылка: `href` на `ExbDetails`
- Станд: `fa-map-marker` + следующий `span`
- Страна: `.card-text`

## Рабочий скрипт
`scripts/parsers/gulfood_dubai.py` — полный парсер с Playwright cookies + urllib pagination

## Пагинация
По 16 компаний на страницу. Для сектора World Food (~3,255 компаний) — ~204 страницы.
