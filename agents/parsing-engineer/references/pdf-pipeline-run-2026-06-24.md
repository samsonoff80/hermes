# PDF Pipeline Run — prodexpo_2024.pdf (24.06.2026)

## Вход
- Файл: `~/audit/prodexpo_2024.pdf` (19MB, 676 страниц)
- Источник для Supabase: `prodexpo_2024_pdf`

## Пайплайн
```
parse_pdf.py → filter_v5.py → normalize_and_dedup.py → Supabase raw_parsed_data
```

## Результаты
| Этап | Вход | Выход | Примечание |
|------|------|-------|------------|
| parse_pdf.py | 676 стр | 1,762 | PyMuPDF, ~55 стр/сек |
| filter_v5.py | 1,762 | 1,580 (89%) | --no-consilium, -182 мусора |
| normalize_and_dedup.py | 1,580 | 1,521 | -59 дублей |
| Supabase upload | 1,580 | ✅ | batch=50, source=prodexpo_2024_pdf |

## Ключевые решения при загрузке в Supabase
1. **Структура таблицы верифицирована**: `id, name, name_clean, country, phone, email, website, description, source, is_duplicate, duplicate_of, dedup_method, dedup_confidence, created_at`
2. **НЕТ полей**: city, address, categories, source_year, raw_data
3. **UUID поля**: `id` и `duplicate_of` — не передавать пустые строки. `id` вообще не включать. `duplicate_of` — передавать None если пусто.
4. **PGRST102 fix**: ВСЕ записи в batch иметь идентичный набор ключей. Опциональные поля (duplicate_of, dedup_method, dedup_confidence) присутствовать всегда с None/пустыми значениями.
5. **is_duplicate**: булево поле, из CSV приходит как строка "True"/"False" — нужно конвертировать.

## Пример рабочего кода загрузки
```python
norm_rec = {
    'name': rec.get('name', '').strip(),
    'name_clean': rec.get('name_clean', '').strip() or rec.get('name', '').strip(),
    'country': rec.get('country', ''),
    'phone': rec.get('phone', ''),
    'email': rec.get('email', ''),
    'website': rec.get('website', ''),
    'description': rec.get('description', ''),
    'source': source_name,
    'is_duplicate': rec.get('is_duplicate', 'False') == 'True',
    'duplicate_of': rec.get('duplicate_of', '') or None,
    'dedup_method': rec.get('dedup_method', '') or None,
    'dedup_confidence': float(rec['dedup_confidence']) if rec.get('dedup_confidence') else None,
}
```
