# Cron-задачи: Проблемы и решения (01.07.2026)

## Проблемы
- Задачи не запускаются (`last_run_at: null`) из-за ошибок доступа к Supabase.
- Скрипты обогащения требуют проверки.

## Решения
1. Проверить `.env` на наличие `SUPABASE_SERVICE_KEY`.
2. Запустить задачи вручную для тестирования:
   ```bash
   hermes cronjob action=run job_id=<ID>
   ```
3. Добавить логирование ошибок в скрипты обогащения.

## Пример ошибки
```
Traceback (most recent call last):
  File "enrich_contacts.py", line 10, in <module>
    supabase: Client = create_client(url, key)
  File "/venv/lib/python3.11/site-packages/supabase/_sync/client.py", line 59, in __init__
    raise SupabaseException("supabase_key is required")
supabase._sync.client.SupabaseException: supabase_key is required
```