# WorldFood Istanbul 2026 — Исправление маппинга колонок (21.06.2026)

## Проблема
Существующий парсер `worldfood_istanbul.py` неправильно маппинг колонки DataTables:
- Предполагалось: `data[0]` → имя через `img[alt]`, `data[1]` → страна, `data[2]` → категории
- Реальность: `data[0]` → logo HTML (img alt ПУСТОЙ), `data[1]` → имя компании, `data[2]` → страна

## Симптомы
- Поле `name` = "Products / ServicesBrochures" для большинства записей
- Поле `country` = название компании (например, "«CHOCO- ARS» LLCNew Exhibitor")
- Поле `categories` = страна (например, "Azerbaijan")

## Решение
```python
# Правильный маппинг:
name = clean_html(row[1])  # col[1] = название
name = re.sub(r'New Exhibitor$', '', name).strip()  # обрезать суффикс
country = clean_html(row[2])  # col[2] = страна
```

## Структура DataTables ответа
```json
{
  "draw": 1,
  "recordsTotal": 478,
  "recordsFiltered": 478,
  "data": [
    [
      "<a href=\"/en/exhibitor-356448-2026.info\"><img alt=\"\" ...></a>...",  // col[0]: logo, alt пустой!
      "COMPANY NAMENew Exhibitor",  // col[1]: имя + суффикс
      "Türkiye"                     // col[2]: страна
    ],
    ...
  ]
}
```

## Результат после исправления
- 478 корректных записей загружено в Supabase (source=`worldfood_istanbul`)
- Примеры: "SARAÇOĞLU KURUYEMİŞ VE GIDA SAN. TİC. LTD. ŞTİ. | Türkiye"
