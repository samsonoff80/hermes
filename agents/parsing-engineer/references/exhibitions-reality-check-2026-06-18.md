# Реальное состояние парсинга выставок — 18.06.2026

## Ключевое открытие: Playwright HF НЕ работает

**Playwright HF** (`https://playwright-browser.onrender.com/fetch?url=`) возвращает **HTTP 206** для всех внешних сайтов. Он отдаёт HTML страницы Hugging Face вместо целевого контента. Всё что было написано в `exhibitions_playwright.py` — не работает.

**Прямой доступ через requests работает** для большинства сайтов.

## Детальный анализ каждого источника

### ✅ WorldFood Moscow — ПОЛНОСТЬЮ ДОСТУПЕН
- **URL**: `https://exhibitors-itegroup.exhibitoronlinemanual.com/worldfood-moscow-2025/en/Exhibitor`
- **Прямой доступ**: 200, 89,966 bytes
- **Селекторы**:
  - Карточки: `.card.h-100` (24 на страницу)
  - Название: `.card-title a` (text-transform: uppercase)
  - Страна: `.card-text` (текст страны, напр. "Russia")
  - Детали: `/ExbDetails/{base64_id}`
- **Пагинация**: 34+ страниц, класс `.pagination`
- **Ожидаемый объём**: ~800 компаний (24 × 34)
- **КРИТИЧНО**: НЕ использовать `.card` без `.h-100` — совпадёт с фильтрами!

### 🔴 WorldFood Istanbul — SPA (данные не в HTML)
- **URL**: `https://worldfood-istanbul.com/en/katilimci-listesi`
- **Прямой доступ**: 200, 100,777 bytes, но список компаний пуст
- **Вывод**: SPA, нужен browser tool

### 🟡 Gulfood Dubai — AJAX-загрузка
- **URL**: `https://exhibitors.gulfood.com/gulfood-2026/Sectorlist/world-food`
- **Прямой доступ**: 200, 243,989 bytes
- **293 `.card` элементов** — это фильтры категорий/стран, НЕ компании
- **AJAX endpoint**: `ajaxPaginationData` найден, но параметры неизвестны
- **Всего компаний**: 6,684 (указано в пагинации)

### 🟡 InterFood Azerbaijan — мало данных в HTML
- **URL**: `https://interfood.az/en/exhibitors`
- **Прямой доступ**: 200, 48,452 bytes
- **4 `.card` элемента** — новости, не компании

### 🟡 UzFood — данные есть, нужны селекторы
- **URL**: `https://uzfoodexpo.uz/en/exhibitors-list`
- **Прямой доступ**: 200, 76,617 bytes
- **17 `.card`** — не компании

### 🔴 FoodExpo Qazaqstan — SPA
- **URL**: `https://foodexpo.kz/`
- **Прямой доступ**: 200, 73,546 bytes, данные не в HTML

### 🟡 Bakery Expo KZ — данные есть, нужны селекторы
- **URL**: `https://all-events.ru/events/bakery-expo-kazakhstan-2025`
- **Прямой доступ**: 200, 183,425 bytes (12,152 chars text)

### 🟡 Modern Bakery Moscow — Tilda, большой HTML
- **URL**: `https://www.modern-bakery.ru/`
- **Прямой доступ**: 200, 698,888 bytes (10,241 chars text)

### ❌ DairyTech — мёртв (таймаут)
### ❌ Агропродмаш — 404

## Рекомендуемый порядок парсинга

1. **WorldFood Moscow** — самый простой, ~800 компаний, работает через requests
2. **Bakery Expo KZ** — большой HTML, нужны селекторы
3. **Modern Bakery** — большой HTML, нужны селекторы
4. **UzFood** — средний HTML, нужны селекторы
5. **Gulfood** — AJAX, нужен доп. анализ
6. **InterFood Azerbaijan** — мало данных, нужен доп. анализ
7. **WorldFood Istanbul, FoodExpo KZ** — SPA, нужен browser tool

## Паттерн для быстрого анализа нового сайта

```python
import requests
from bs4 import BeautifulSoup
import re

headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

r = requests.get(url, headers=headers, timeout=20)
soup = BeautifulSoup(r.text, 'html.parser')

# 1. Объём текста
text = soup.get_text(strip=True)
print(f"Text length: {len(text)}")

# 2. Классы с упоминанием company/exhibitor
all_classes = set()
for tag in soup.find_all(True):
    for cls in tag.get('class', []):
        all_classes.add(cls)
company_classes = [c for c in all_classes if any(kw in c.lower() for kw in ['exhibit', 'company', 'firm', 'participant'])]
print(f"Company classes: {company_classes}")

# 3. JSON data в скриптах + AJAX endpoints
for s in soup.find_all('script'):
    if s.string and ('exhibitor' in s.string.lower() or 'company' in s.string.lower()):
        ajax_urls = re.findall(r'["\']([^"\']*(?:ajax|api|fetch)[^"\']*)["\']', s.string, re.I)
        if ajax_urls:
            print(f"AJAX URLs: {ajax_urls}")

# 4. Таблицы
tables = soup.find_all('table')
print(f"Tables: {len(tables)}")
```
