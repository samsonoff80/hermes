# System Health Check — 18.06.2026 03:50 (UTC+3)

## Инфраструктура

| Сервис | Статус | Деталы |
|--------|--------|--------|
| Интернет (прямой) | ✅ | 200, 0.24s |
| Proton Proxy | ✅ | 200, 0.46s |
| Playwright HF | ⚠️ Degraded | 206 Partial Content, health возвращает HTML "Preparing Space" |
| Supabase | ✅ | REST API работает |
| .env | ✅ | Ключи читаются |

## Supabase

| Таблица | Записи | Примечание |
|---------|--------|------------|
| raw_parsed_data | 24,806 | ~24,600 — дубликаты Продэкспо |
| clean_clients | **0** | Пустая |
| clients | 1000+ | Архивная |

## Cron-задачи

| Задача | Статус |
|--------|--------|
| playwright-keepalive | ✅ OK |
| layer4-daily-clean | ⏳ Следующий: 08:00 |
| layer3-parse | ❌ RuntimeError на последнем запуске |
| layer2-weekly-scout | ⏳ Следующий: пн 09:00 |
| SalesBot Update Free Models | ✅ OK |
| SalesBot Funnel Follow-up | ✅ OK |
| SalesBot Reactivation | ⏳ Следующий: пн 10:00 |

## Ключевые проблемы

1. **clean_clients пуст** — layer4-daily-clean ещё не запускался сегодня
2. **layer3-parse упал** — RuntimeError, но отчёт был содержательным
3. **Playwright HF спит** — не использовать для парсинга
4. **Security scan блокирует pipe-to-python** — влияет на cron-задачи
5. **24K+ дубликатов Продэкспо** — нужна дедупликация

## Следующие шаги

1. Запустить layer4 clean_data.py для очистки raw_parsed_data
2. Дедуплицировать Продэкспо в raw_parsed_data
3. Исправить layer3-parse cron (RuntimeError)
4. Мониторить Playwright HF — возможно потребуется перезапуск Space
