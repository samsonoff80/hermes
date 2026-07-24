# WorldFood Istanbul 2026 — Парсинг через ERA Soft DataTables API

**Дата**: 21.06.2026
**Платформа**: ERA Soft LLC
**URL**: https://worldfood-istanbul.com/en/exhibitor-list
**Всего экспонентов**: 478

## API Endpoint

```
POST https://worldfood-istanbul.com/ERAForms/companies_list.php?l=en&exhibition=30&y=2026
```

### Параметры POST (DataTables server-side processing)
- `draw=1` — номер запроса
- `start=0` — offset
- `length=100` — записей на страницу (макс 100)
- `search[value]=` — поиск (пусто = все)
- `search[regex]=false`
- `order[0][column]=0` — сортировка по первой колонке
- `order[0][dir]=asc`

### Заголовки
- `X-Requested-With: XMLHttpRequest` — обязательно для AJAX
- `Content-Type: application/x-www-form-urlencoded`
- `Referer: https://worldfood-istanbul.com/en/exhibitor-list`

### Структура ответа
```json
{
  "draw": 1,
  "recordsTotal": 478,
  "recordsFiltered": 478,
  "data": [
    ["<a href=\"/en/exhibitor-356448-2026.info\" ...><img alt=\"COMPANY NAME\" .../></a>...", "Country", "Categories"],
    ...
  ]
}
```

### Парсинг полей
- `data[0]` — HTML logo-block: `img[alt]` = название компании, `a[href]` = URL детальной страницы
- `data[1]` — страна (текст)
- `data[2]` — категории продуктов (текст)

### Питфоллы
1. **Прямой GET /en/exhibitor-list** — возвращает HTML-каркас (59KB) без данных. Данные загружаются через JS.
2. **GET /en/exhibitors** — лендинг-страница (100KB), только навигация и партнёры, нет списка экспонентов.
3. **Без X-Requested-With** — API может вернуть пустой ответ или редирект.
4. **Source name в Supabase**: `worldfood_istanbul` (не `worldfood_istanbul_2025`)

### Скрипт
`scripts/parsers/worldfood_istanbul.py`

### Детальная страница экспонента
URL формат: `https://worldfood-istanbul.com/en/exhibitor-{id}-2026.info`
Содержит: описание, категории продуктов, контакты (если доступны)
