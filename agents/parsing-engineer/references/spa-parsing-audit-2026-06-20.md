# SPA-парсинг: аудит 20.06.2026

## Проверенные SPA-сайты

### Gulfood Dubai
- URL: `https://exhibitors.gulfood.com/gulfood-2026/Sectorlist/world-food`
- 244KB HTML, 294 `.card` элемента = **список стран**, не компании
- Компании загружаются при клике на страну через AJAX
- Прямой AJAX вызов возвращает 404 (JS проверяет URL segment)
- **Статус**: Нужен browser tool или поиск скрытого API endpoint

### Modern Bakery Moscow
- URL: `https://www.modern-bakery.ru/`
- 699KB HTML, Tilda SPA
- `.t-name` (173) = навигация, `.t-rec` (64) = контейнеры навигации
- `/catalog` и `/exhibitors_list` — 90KB HTML без данных компаний
- **Статус**: Нужен browser tool для рендеринга Tilda AJAX

### UzFood (uzfoodexpo.uz)
- URL: `https://uzfoodexpo.uz/en/exhibitors-list`
- 76KB HTML (85KB после Playwright рендеринга)
- Использует jQuery DataTables — данные загружаются через AJAX
- `li.item` (170) = навигация языков (UZ/EN/RU), не компании
- Перехват XHR не выявил API endpoint (только Яндекс.Метрика)
- **Статус**: Нужен полноценный браузер с перехватом Network

### DairyTech
- URL: `https://www.dairytechexpo.ru/`
- DNS не резолвится (NameResolutionError)
- **Статус**: ❌ DEAD

### Bakery Expo KZ
- URL: `https://all-events.ru/events/bakery-expo-kazakhstan-2025/`
- 174KB HTML, `.event-date` (42), `.event-title` (14)
- Это календарь событий, не каталог компаний
- **Статус**: ⚠️ Неподходящий тип источника

## Инструменты

### Playwright локальный (работает!)
- `playwright.sync_api.sync_playwright` + `chromium.launch(headless=True)`
- Chromium 148 для ARM64 установлен
- `page.goto(url, wait_until="networkidle")` + `page.wait_for_timeout(5000)`
- Перехват: `page.on("response", callback)` / `page.on("request", callback)`
- Ограничение: HTML рендерится, но данные могут требовать отдельных XHR

### Proton Proxy (НЕ работает для SPA)
- Возвращает 100-200 bytes для SPA-сайтов
- UzFood: 223B, Gulfood: 1110B, Modern Bakery: 1081B

### browser tool (недоступен)
- Ошибка: `/usr/bin/env: 'node': No such file or directory`

## Рекомендации
1. Для Gulfood: попробовать найти скрытый API endpoint через анализ всех JS-файлов на странице
2. Для UzFood: искать DataTables `ajax` конфигурацию в `data-` атрибутах таблицы
3. Для Modern Bakery: искать Tilda API project/page ID и эндпоинт каталога
4. DairyTech и Bakery Expo KZ — исключить из парсинга
