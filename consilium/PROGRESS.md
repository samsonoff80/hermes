# Consilium — Прогресс

## 03.07.2026 — Единый управляющий провайдерами
- provider_health.py объединил update_model.py + update_fallback.py
- Проверяет доступность всех провайдеров каждый час
- Блокирует недоступных в provider_state.json
- Выбирает первого доступного как основную модель
- Обновляет fallback (исключает заблокированных)
- Перезапускает Hermes если основная изменилась
- Добавлен мониторинг shir-man.com для новых бесплатных моделей
- Mistral, Groq, SambaNova добавлены в custom_providers

## 02.07.2026 — Circuit Breaker
- providers.py: авто-блокировка при 429 (1ч), 401/402/403 (24ч)
- Все 8+ провайдеров в fallback (НЕ удалять!)
- provider_health.py в cron каждый час
- Инженер (optimizer) обновлён
