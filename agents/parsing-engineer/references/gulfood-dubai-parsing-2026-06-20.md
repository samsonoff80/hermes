# Gulfood Dubai 2026 — парсинг через AJAX API

**Открыто:** 20.06.2026

## Платформа
Та же платформа `exhibitoronlinemanual.com`, что и WorldFood Moscow, но другой AJAX endpoint.

## AJAX Endpoint
```
POST https://exhibitors.gulfood.com//Sectorlist/ajaxPaginationData/{page}
```
**Важно:** двойной слеш в пути (`//Sectorlist/`).

## Параметры POST
```
ExhibitorDataView=1&event_id=72&sortBy=&page={page}&keyword_search=&selectedCountries=&InitialKey=&selectedCategories=&selectedSubCategories=&selectedSubSubCategories=&selectedVenues=&selectedSectors=%5B%22World+Food%22%5D&event_slug=gulfood-2026&sector_slug=world-food
```

## Заголовки
- `Cookie` — **обязателен**, берётся из начальной загрузки страницы (AWSALB + ci_sessions)
- `X-Requested-With: XMLHttpRequest`
- `Referer: https://exhibitors.gulfood.com/gulfood-2026/Sectorlist/world-food`

## Получение cookies
```python
req = urllib.request.Request("https://exhibitors.gulfood.com/gulfood-2026/Sectorlist/world-food", headers={'User-Agent': '...'})
with urllib.request.urlopen(req, timeout=20) as resp:
    cookies = resp.headers.get_all('Set-Cookie')
    cookie_str = '; '.join(c.split(';')[0] for c in cookies)
```

## Структура ответа
HTML с элементами `<div class="item mb-4">`:
- Название: `<a class="exb-title">` 
- Стенд: `<i class="fa fa-map-marker">` → текст после `&nbsp;`
- Детальная страница: `href=".../ExbDetails/..."`

## Пагинация
- 16 компаний на страницу
- ~3,255 компаний в секторе World Food (204 страниц)
- Номера страниц: 0, 1, 2, ...

## Селектор для парсинга
```python
items = re.findall(r'<div class="item mb-4">(.*?)</div>\s*</div>', html, re.DOTALL)
for item in items:
    name_match = re.search(r'class="exb-title"[^>]*>\s*(.+?)\s*</a>', item, re.DOTALL)
    name = name_match.group(1).strip() if name_match else ''
    name = re.sub(r'&[a-z]+;', '', name).strip().strip('"').strip()
    
    stand_match = re.search(r'fa fa-map-marker[^>]*>\s*(?:&nbsp;)?([^<]+)</a>', item)
    stand = stand_match.group(1).strip() if stand_match else ''
    
    url_match = re.search(r'href="([^"]*ExbDetails[^"]*)"', item)
    detail_url = url_match.group(1) if url_match else ''
```

## Питфоллы
- Proton Proxy возвращает 405 для POST-запросов — работает только GET
- Без cookies из начальной загрузки AJAX возвращает 404
- `getData()` из JS контекста страницы использует URL с опечаткой `/Exhibitos/` вместо `/Sectorlist/` — не работает
- Нужно использовать прямой POST с полными параметрами и cookies

## Статус
- Парсинг работает, но упал по таймауту на ~100-й странице
- Файл: `data/gulfood_dubai_2026.json` (неполный, требует догрузки)
- Загрузка в Supabase: не выполнена
