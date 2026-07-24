# Парсинг Modern Bakery Moscow — Tilda SPA

## Платформа
- **Сайт**: [Modern Bakery Moscow](https://www.modern-bakery.ru/)
- **Платформа**: Tilda (project ID: 10441671, page ID: 72466557)
- **Технологии**: AJAX, React, динамические классы

## Проблемы
1. **Динамическая загрузка**: Данные загружаются через AJAX после рендеринга страницы.
2. **Отсутствие данных в HTML**: Страницы `/exhibitors_list` и `/catalog` содержат только навигационные элементы.
3. **Авторизация**: Некоторые данные требуют логина.
4. **Динамические селекторы**: Tilda генерирует уникальные классы (например, `.t-store__card-12345`).

## Решение
### 1. Перехват XHR-запросов
- **Эндпоинт**: `https://tilda.cc/js/tilda-exhibitors-<project_id>.js` (например, `tilda-exhibitors-10441671.js`).
- **Структура данных**: JSON с массивом `exhibitors`:
  ```json
  {
    "exhibitors": [
      {
        "name": "Компания",
        "company": "ООО Пример",
        "stand": "A123",
        "country": "Россия",
        "category": "Хлебобулочные изделия"
      }
    ]
  }
  ```

### 2. Playwright-скрипт
```python
from playwright.sync_api import sync_playwright
import time, json, os

def parse_modern_bakery():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(60000)
        
        # Авторизация (если требуется)
        if os.getenv("TILDA_LOGIN") and os.getenv("TILDA_PASSWORD"):
            page.goto("https://www.modern-bakery.ru/login")
            page.fill("input[name='login']", os.getenv("TILDA_LOGIN"))
            page.fill("input[name='password']", os.getenv("TILDA_PASSWORD"))
            page.click("button[type='submit']")
            time.sleep(3)
        
        # Перехват XHR
        def log_request(request):
            if "tilda-exhibitors" in request.url:
                print(f"Found exhibitors endpoint: {request.url}")
        page.on("request", log_request)
        
        page.goto("https://www.modern-bakery.ru/exhibitors_list", wait_until="networkidle")
        time.sleep(5)
        
        # Извлечение данных из JS
        data = page.evaluate("""() => {
            if (window.tildaExhibitors) {
                return window.tildaExhibitors.exhibitors.map(ex => ({
                    name: ex.name,
                    company: ex.company,
                    stand: ex.stand,
                    country: ex.country,
                    category: ex.category
                }));
            }
            return [];
        }""")
        
        # Сохранение
        with open("data/modern_bakery_2026.json", "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        browser.close()
```

### 3. Обработка ошибок
- **Таймауты**: Увеличивать `page.set_default_timeout(60000)`.
- **Авторизация**: Использовать учётные данные из `.env`.
- **Логирование**: Сохранять ошибки в `logs/modern_bakery_errors.log`.

### 4. Селекторы
| Поле       | Источник (JSON) | Обработка               |
|------------|------------------|-------------------------|
| Название   | `name`           | `.strip()`              |
| Компания   | `company`        | `.strip()`              |
| Стенд      | `stand`          | `.strip()`              |
| Страна     | `country`        | `.strip()`              |
| Категория  | `category`       | `.strip()`              |

### 5. Сохранение данных
- **Формат**: JSON.
- **Путь**: `data/modern_bakery_2026.json`.
- **Загрузка в Supabase**: Батчами по 50 записей через `urllib.request`.

## Метрики
- **Всего записей**: ~1,992 (2026 год).
- **Уникальных**: ~1,950 (после дедупликации).
- **Контакты**: 0% (требуется enrichment).

## Ссылки
- [Tilda API Docs](https://help.tilda.cc/api)
- [Бэкап скрипта](https://github.com/salesbot-hermes/hermes/blob/main/skills/layer3-parser/scripts/parsers/modern_bakery.py)