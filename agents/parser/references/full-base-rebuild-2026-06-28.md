# Полная пересборка базы с нуля — 28.06.2026

## Контекст
Пользователь запросил полный сброс базы (raw_parsed_data + clean_clients) и перезапуск всех 4 слоёв с нуля.

## Выполненные этапы

### Этап 1: Очистка
- `DELETE ?id=gt.0` для raw_parsed_data и clean_clients (работает)
- source_profiles очищен по ID (batch DELETE по 100)
- Результат: все таблицы пустые

### Этап 2: Scout (auto_scout_v2)
- web_search для 9 стран СНГ × категории
- Найдено 21 URL, проверено curl: 18 доступны
- Фильтр: оставлены реальные каталоги (6 источников)

### Этап 3: Source Profiles
- Загружено 5 профилей в source_profiles:
  - fabricators.ru Pischevaya
  - rfactories Pischevaya
  - areg.am Armenia Food
  - manufacturers Armenia
  - manufacturers Tajikistan

### Этап 4: Парсинг
- Универсальный парсер (regex-based) для каждого источника
- 3,605 сырых → 3,009 уникальных (дедуп по name+country)
- Загружено в raw_parsed_data

### Этап 5: Pipeline V5.5
- 3,009 → 2,675 (11.1% rejected: low_score, fuzzy_dedup)
- Фильтр не-СНГ: -428 (Китай, Турция, Корея, Италия...)
- Нормализация стран: "Республика Беларусь" → "Беларусь" и т.д.
- **Финально в clean_clients: 2,247 записей (СНГ only)**

### Этап 6: Обогащение контактов (В ПРОЦЕССЕ)
- web_search через execute_code, батчи по 25
- Hit rate ~30-65% (зависит от типа компаний)
- Прогресс сохраняется в /tmp/enrich_progress_final.json

## Распределение по странам (clean_clients)
| Страна | Записей |
|--------|---------|
| Россия | 1,688 |
| Казахстан | 156 |
| Армения | 134 |
| Беларусь | 98 |
| Грузия | 54 |
| Узбекистан | 45 |
| Туркменистан | 41 |
| Кыргызстан | 18 |
| Азербайджан | 13 |

## Ключевые ошибки и решения

### 1. DuckDuckGo API не работает для контактов
**Проблема:** enrich_v2.py через DuckDuckGo API/HTML дал 0% hit rate
**Решение:** Только web_search (встроенный в Hermes) работает (60-67% hit rate)

### 2. OpenRouter free модели rate-limited
**Проблема:** Все бесплатные модели (hermes-3-405b, llama-3.3-70b, gemma-2-27b) вернули 429
**Решение:** Не использовать OpenRouter free для batch-задач

### 3. enrich_contacts.py (Groq LLM) — не использовать
**Проблема:** LLM выдумывает номера телефонов + `.is_('phone','null')` падает
**Решение:** web_search + regex извлечение из snippet

### 4. execute_code таймаут 300с
**Проблема:** Батчей >25 записей не помещается в таймаут
**Решение:** Батчи по 25, прогресс в файл, возобновление

### 5. Supabase REST `id=not.in.()` медленный
**Проблема:** Большие IN (>100 ID) тормозят запрос
**Решение:** Загружать limit=1000 по оффсету, фильтровать локально

### 6. Background terminal + Python = tcsetattr hang
**Проблема:** `terminal(background=True, command="python3 ...")` → exit 143
**Решение:** Использовать execute_code напрямую для Python с web_search

## Правильный паттерн обогащения (28.06.2026)

```python
# В execute_code (НЕ standalone!):
from hermes_tools import web_search

# 1. Загрузить записи без контактов (limit=1000, offset)
# 2. Фильтровать локально: not r.get('phone') and not r.get('email') and not r.get('website')
# 3. Батчей по 25:
for batch in chunks(records, 25):
    for r in batch:
        name = re.sub(r'[,.]?\s*(ООО|ТОО|...)\s*$', '', r['name_clean'], flags=re.I)
        result = web_search(f"{name} {r['country']} телефон email сайт", limit=3)
        # Извлечь из title + description + snippet
        # Валидировать phone/email/website
        sb_patch(r['id'], {'phone': ..., 'email': ..., 'website': ...})
        time.sleep(0.1)
    # Сохранить прогресс каждые 25
    save_progress()
```

## Метрики производительности
- web_search: ~25 записей за 200с (limit=3, sleep=0.1)
- Для 2,247 записей: ~90 батчей × 200с = ~5 часов
- Hit rate: 30-65% (в среднем ~40%)
- Ожидаемый результат: ~900 обогащённых записей
