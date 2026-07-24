# CIS Whitelist Cleanup — 27.06.2026

## Контекст
Пользователь привёл базу clean_clients к строгому whitelistу СНГ (без Беларуси).

## Whitelist (9 стран)
```
Россия, Казахстан, Узбекистан, Армения, Азербайджан, Кыргызстан, Грузия, Таджикистан, Туркменистан
```

## Что удалять
1. **Беларусь** — все варианты: "Беларусь", "Belarus", "Республика Беларусь", "РБ", "Byelarus"
2. **Не-СНГ** — всё что не в whitelist (Европа, Азия, Ближний Восток, Африка, Америка)
3. **Пустое поле** — NULL или "" в country
4. **Мусор в country** — "Название ООО, Россия" → нормализовать если СНГ, удалить если не-СНГ
5. **Стенды/залы** — name_clean содержит "пав", "зал", "стенд", "pav", "hall", "stand"
6. **Короткие имена** — len(name_clean) < 5

## Алгоритм очистки
```python
VALID = {"Россия", "Казахстан", "Узбекистан", "Армения", "Азербайджан",
         "Кыргызстан", "Грузия", "Таджикистан", "Туркменистан"}

def is_cis(country):
    if not country: return False
    # Exact match
    if country in VALID: return True
    # "Россия, г. Москва," pattern
    if country.strip().lower().startswith("росси"): return True
    return False

# Delete non-CIS in batches of 500
for i in range(0, len(ids_to_delete), 500):
    batch = ids_to_delete[i:i+500]
    filters = ",".join(str(x) for x in batch)
    url = f"{SU}/rest/v1/clean_clients?id=in.({filters})"
    req = urllib.request.Request(url, method="DELETE", headers=...)
```

## Результат
- Было: 19,463 → Стало: 7,000
- Удалено: 12,463 (64%)
- Экономия Serper: ~12K запросов не потрачены на мусор

## Важно: порядок операций
1. **Сначала очистка** — удалить не-СНГ, мусор, пустые
2. **Потом обогащение** — Serper на чистой базе
Это экономит API запросы и токены LLM.
