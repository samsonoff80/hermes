# Парсинг Gulfood Dubai 2026 — AJAX API

## Платформа
- **Сайт**: [Gulfood Dubai 2026](https://exhibitors.gulfood.com/)
- **Платформа**: `exhibitoronlinemanual.com` (DataTables server-side processing)
- **Технологии**: jQuery, AJAX, cookies (`AWSALB`, `ci_sessions`)

## Проблемы
1. **Динамическая загрузка**: Данные загружаются через AJAX после рендеринга страницы.
2. **Блокировки**: Прямые запросы к API блокируются после 50 страниц (HTTP 403).
3. **Таймауты**: Загрузка страниц >100 занимает до 30 секунд.
4. **Селекторы**: Названия компаний содержат суффикс `New Exhibitor`.

## Решение
### 1. Перехват AJAX-запросов
- **Эндпоинт**: `POST https://exhibitors.gulfood.com//Sectorlist/ajaxPaginationData/{page}` (двойной слеш!).
- **Параметры**:
  ```json
  {
    "draw": 1,
    "start": 0,
    "length": 16,
    "search[value]": "",
    "order[0][column]": 0,
    "order[0][dir]": "asc",
    "event_id": 72,
    "selectedSectors": ["World Food"],
    "event_slug": "gulfood-2026",
    "sector_slug": "world-food"
  }
  ```
- **Cookies**: Обязательны `AWSALB` и `ci_sessions` из начальной загрузки страницы.

### 2. Playwright-скрипт
```python
from playwright.sync_api import sync_playwright
import time, json, os, itertools

# Прокси-ротация
proxies = itertools.cycle(os.getenv("PROXY_LIST", "").split(","))

def parse_gulfood():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(60000)
        
        # Начальная загрузка для получения cookies
        page.goto("https://exhibitors.gulfood.com/en/exhibitors-list", wait_until="networkidle")
        time.sleep(5)
        cookies = context.cookies()
        
        # AJAX-пагинация
        for page_num in range(1, 205):  # 204 страницы по 16 записей
            try:
                proxy = next(proxies)
                print(f"Using proxy: {proxy}")
                
                data = {
                    "draw": page_num,
                    "start": (page_num - 1) * 16,
                    "length": 16,
                    "search[value]": "",
                    "order[0][column]": 0,
                    "order[0][dir]": "asc",
                    "event_id": 72,
                    "selectedSectors": ["World Food"],
                    "event_slug": "gulfood-2026",
                    "sector_slug": "world-food"
                }
                
                response = page.request.post(
                    f"https://exhibitors.gulfood.com//Sectorlist/ajaxPaginationData/{page_num}",
                    data=data,
                    headers={"X-Requested-With": "XMLHttpRequest"},
                    timeout=60000
                )
                
                if response.status != 200:
                    print(f"Failed to fetch page {page_num}: HTTP {response.status}")
                    continue
                
                result = response.json()
                for item in result.get("data", []):
                    name = item[1].replace("New Exhibitor", "").strip()
                    country = item[2].strip()
                    stand = re.search(r'\d{1,3}-\d{2,4}', item[3]).group(0) if re.search(r'\d{1,3}-\d{2,4}', item[3]) else ""
                    
                    # Сохранение в Supabase
                    record = {
                        "name": name,
                        "name_clean": name,
                        "country": country,
                        "phone": "",
                        "email": "",
                        "website": "",
                        "description": f"Gulfood Dubai 2026, стенд: {stand}",
                        "source": "gulfood_dubai_2026",
                        "is_duplicate": False,
                        "duplicate_of": None,
                        "dedup_method": None,
                        "dedup_confidence": None
                    }
                    # Загрузка батчами по 50 записей
                    ...
                
                time.sleep(1)  # Задержка между запросами
                
            except Exception as e:
                print(f"Error on page {page_num}: {str(e)}")
                continue
        
        browser.close()
```

### 3. Обработка ошибок
- **Таймауты**: Повторять запрос с экспоненциальной задержкой (3 попытки).
- **Блокировки**: При HTTP 403/429 менять прокси и User-Agent.
- **Логирование**: Сохранять ошибки в `logs/gulfood_errors.log`.

### 4. Селекторы
| Поле       | Селектор (JSON) | Обработка                          |
|------------|------------------|-------------------------------------|
| Название   | `item[1]`        | `replace("New Exhibitor", "")` |
| Страна     | `item[2]`        | `.strip()`                          |
| Стенд      | `item[3]`        | `re.search(r'\d{1,3}-\d{2,4}')`   |

### 5. Сохранение данных
- **Формат**: JSON Lines (`*.jsonl`).
- **Путь**: `data/gulfood_dubai_2026.jsonl`.
- **Загрузка в Supabase**: Батчами по 50 записей через `urllib.request`.

## Метрики
- **Всего записей**: ~3,255 (204 страницы × 16 записей).
- **Уникальных**: ~3,200 (после дедупликации).
- **Контакты**: 0% (требуется enrichment).

## Ссылки
- [Бэкап скрипта](https://github.com/salesbot-hermes/hermes/blob/main/skills/layer3-parser/scripts/parsers/gulfood_dubai.py)
- [Прокси-ротация](references/proxy-rotation-for-parsers-2026-07-02.md)