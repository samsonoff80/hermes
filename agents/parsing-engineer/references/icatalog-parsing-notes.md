# Парсинг icatalog.expocentr.ru — каталоги выставок Продэкспо

## Структура сайта

### URL паттерны
- Список компаний: `https://icatalog.expocentr.ru/ru/exhibitions/{exhibition_id}/list`
- По странам: `.../countries`
- По алфавиту: `.../alphabet`

### Известные exhibition_id
| Год | ID | Компаний |
|-----|-----|----------|
| 2026 | `870c9c18-e84b-11ef-80ce-a0d3c1fab97f` | 1992 |
| 2025 | `b5cf5aaa-3c26-11ee-80ce-a0d3c1fab97f` | 1799 |
| 2024 | `97cfb9c0-dfee-11ec-80cd-a0d3c1fab97f` | 2148 |

## Метод парсинга списка

```python
import urllib.request, re
html = urllib.request.urlopen(url, timeout=20).read().decode('utf-8')
rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
for row in rows[1:]:
    cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
    clean = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
    # [0]=name, [1]=country, [2]=pavilion, [3]=stand, [4]=categories
```

## Ограничения
- Контакты (phone/email/website) НЕ в списке — только на детальных страницах
- Детальные страницы через JS — прямых URL нет
- Парсинг 6000+ страниц нецелесообразен
- Для контактов используйте prodexpo_full.json (678 записей)
