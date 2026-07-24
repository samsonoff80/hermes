# Pipeline V5.5 — Прогресс

## 02.07.2026 — Исправление fallback_providers и Circuit Breaker

### Проблема
- `fallback_providers` в `config.yaml` содержал недоступных провайдеров:
  - **Cloudflare**: `429 rate_limited`
  - **GitHub**: `401 Unauthorized`
  - **OpenRouter**: `429 rate_limited`
  - **Mistral**: `429 rate_limited`
  - **SambaNova**: `429 rate_limited`
- Hermes тратил время на ретраи к заблокированным провайдерам.

### Выполненные действия
1. **Проверка провайдеров**
   - Запущен `provider_health.py` для всех провайдеров из `fallback_providers`.
   - **Результаты**:
     | Провайдер    | Статус               | Причина               |
     |--------------|----------------------|-----------------------|
     | Mistral      | 🚫 Заблокирован      | `rate_limited`        |
     | Groq         | ✅ Работает          | —                     |
     | SambaNova    | 🚫 Заблокирован      | `rate_limited`        |
     | Cloudflare   | 🚫 Заблокирован      | `rate_limited`        |
     | GitHub       | 🚫 Заблокирован      | `401 Unauthorized`    |
     | OpenRouter   | 🚫 Заблокирован      | `rate_limited`        |

2. **Обновление `fallback_providers`**
   - Оставлен только **Groq** (единственный рабочий провайдер).
   - Изменено через `hermes config set fallback_providers "[{'model': 'llama-3.3-70b-versatile', 'provider': 'groq'}]"`.

3. **Проверка Circuit Breaker**
   - **`credential_pool.py`**:
     - Обрабатывает ошибки `429` и `401` с cooldown (1 час и 5 минут соответственно).
     - Метод `_mark_exhausted` обновляет статус провайдера и сохраняет его в `auth.json`.
     - Метод `has_available()` фильтрует провайдеры, которые не в cooldown.
   - **Вывод**: Circuit Breaker работает корректно.

4. **Очистка кэша и перезапуск Hermes**
   - Удалены `__pycache__` и `.pyc` файлы.
   - Перезапущен Hermes: `systemctl --user restart hermes-agent`.

### Результаты
- Hermes больше не тратит время на ретраи к заблокированным провайдерам.
- `fallback_providers` содержит только рабочие провайдеры.
- Circuit Breaker корректно блокирует недоступные провайдеры.

---

## 27.06.2026 — Consilium аудит (5 моделей) + оптимизация скоринга
- BAD_KEYWORDS: убраны STAND/BOOTH/EXHIBITION/CATALOG (слишком общие), добавлены EXPO/FAIR/CONFERENCE/SEMINAR/FORUM/EVENT/ORGANIZER/AGENCY/PUBLISHER/PRINTING/ADVERTISING/MARKETING/CONSULTING/LOGISTICS/TRANSPORT/WAREHOUSE/RETAIL/PACKAGING
- GOOD_WORDS_EXACT: добавлены CONFECTIONERY, CHOCOLATE, CANDY, BISCUIT, WAFFLE, PASTRY, CHEESE, BUTTER, ICE_CREAM, BABY_FOOD, PUREE, CEREAL, FORMULA, BAKERY, FLOUR, MARGARINE, MAYONNAISE, FROZEN_FOOD, READY_MEALS, SNACKS, CHIPS, CRACKERS, NUTS, DRIED_FRUITS, INGREDIENTS, ADDITIVES, PRESERVES, JAM, SYRUP, DISTRIBUTION, WHOLESALER
- GOOD_WORDS_PREFIX: добавлены ОРЕХ, СУХО, ЗАМОРО, СНЕК, ДЕТСКО, МАСЛ, ЖИР, МОЛОК
- NON_FOOD: добавлены WHOLESALE_NONFOOD, PACKAGING, LOGISTICS_NONFOOD
- Метрики: reject rate 14.0% → 12.5% (меньше ложных срабатываний)
- Также: убран неиспользуемый импорт hashlib, исправлен RE_COUNTRY_SUFFIX regex, исправлен RE_ADDRESS (lookahead), ExactDedup+FuzzyDedup импортируются из dedup/ модулей (−121 строка)

## Запуск 26.06.2026

### Входные данные
- **raw_parsed_data** (Supabase): 72 153 записей
- **audit/raw_parsed_data_full.csv**: 8 542 записи
- Дедуп по id: 3 938 новых из audit
- **Итого на вход:** 76 091 записей

### Pipeline V5.5
- Обработано: **76 091** записей
- Принято: **23 586** (31.0%)
- Отсеяно: **52 505** (69.0%)
- Серая зона: **16 993** (22.3%)
- Скорость: 6 754 rec/s
- Время: 11.3 сек

### Топ-3 причины отсева
1. **fuzzy_dedup**: 26 927 (нечёткие дубли)
2. **exact_dedup**: 12 673 (точные дубли)
3. **high_score:45 + fuzzy**: 7 433 (прошли скоринг, но дубли)

### Загрузка в Supabase
- clean_clients: **23 586** записей
- Ошибки: 0
- Время: 74 сек

### Файлы
- ~/all_raw_data.csv — полный вход (22 MB)
- ~/clean_all.csv — чистый выход (5.9 MB)
- ~/.hermes/skills/layer4-cleaner/metrics.json — метрики
- ~/.hermes/skills/layer4-cleaner/rejected.csv — отвергнутые (10K записей)