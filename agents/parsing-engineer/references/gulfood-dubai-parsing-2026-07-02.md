---
title: Gulfood Dubai 2026 — Парсинг и проблемы
created: 2026-07-02
updated: 2026-07-02
---

# Gulfood Dubai 2026 — Парсинг и проблемы

## Структура сайта
- **URL**: `https://www.gulfood.com/exhibitors`
- **AJAX-пагинация**: POST `/Sectorlist/ajaxPaginationData/{page}`
  - **Payload**: `{"page":{page},"per_page":24,"sector_id":null,"search_term":""}`
  - **Headers**: `X-Requested-With: XMLHttpRequest`
- **Карточка компании**: `/exhibitor/{slug}/`

## Проблемы и решения

### 1. AJAX возвращает HTML, а не JSON
**Ошибка:**
```
Error fetching page 1: Expecting value: line 2 column 1 (char 1)
```

**Причина:**
- Сервер возвращает HTML-сниппет для рендеринга на стороне клиента.

**Решение:**
- Парсить HTML через `BeautifulSoup`, а не `json.loads`.
  ```python
  response = requests.post(ajax_url, data=payload, headers=headers)
  soup = BeautifulSoup(response.text, 'html.parser')
  companies = soup.select('.exb-title')
  ```

### 2. Таймауты при загрузке страниц
**Ошибка:**
```
TimeoutError: Navigation timeout of 60000 ms exceeded
```

**Решение:**
- Увеличить таймаут до **120 секунд**.
- Отключить `wait_until="networkidle"` (заменить на `domcontentloaded`).
- Добавить повторные попытки при таймауте.
  ```python
  page.goto(url, timeout=120000, wait_until="domcontentloaded")
  ```

### 3. Мусорные данные в именах
**Проблема:**
- Имена типа `N/A`, `1111111`, или короче 3 символов.

**Решение:**
- Фильтровать данные перед загрузкой в пайплайн.
  ```python
  if len(name) < 3 or re.match(r'^\d+$', name) or name.upper() == "N/A":
      continue
  ```

### 4. Нецелевые страны
**Проблема:**
- Компании из UAE, Китая, Индии, Турции.

**Решение:**
- Фильтровать по списку целевых стран.
  ```python
  TARGET_COUNTRIES = ["Россия", "Казахстан", "Узбекистан", "Армения", "Азербайджан", "Кыргызстан", "Таджикистан", "Туркменистан", "Грузия"]
  if company.get("country") not in TARGET_COUNTRIES:
      continue
  ```

### 5. Отсутствие контактов
**Проблема:**
- Выставочные данные редко содержат телефоны/email.

**Решение:**
- Запускать обогащение контактов через `web_search` после загрузки в `raw_parsed_data`.
  ```python
  query = f'"{name}" {country} контакты телефон email сайт'
  ```

## Результаты парсинга
- **Спарсено**: 275 компаний (из ~3264).
- **Загружено в Supabase**: 238 записей (после фильтрации мусора).
- **Pipeline V5.5**: 112 записей очищены, 124 в серой зоне.

## Скрипты
- **Основной парсер**: `~/.hermes/skills/layer3-parser/scripts/parsers/gulfood_dubai.py`
- **Фильтрация данных**: `~/.hermes/skills/layer3-parser/scripts/clean_gulfood_data.py`

## Ссылки
- [Gulfood Dubai Exhibitors](https://www.gulfood.com/exhibitors)
- [Playwright AJAX-парсинг](https://playwright.dev/python/docs/network)