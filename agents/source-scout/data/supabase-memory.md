# Supabase Memory — работа с памятью через Supabase

## Назначение
Таблица `hermes_memory` в Supabase используется как внешняя память для сохранения контекста между сессиями. Используется парсером для восстановления состояния после context compaction.

## Подключение

```python
import requests, json, time, uuid

SUPABASE_URL = 'https://zimojaemhuapieeaxetd.supabase.co'
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')  # из ~/.hermes/.env

HEADERS = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json'
}

BASE = f'{SUPABASE_URL}/rest/v1'
```

## Функции

### Генерация session_id
```python
def make_session_id(task_name: str) -> str:
    return f"{task_name}_{int(time.time())}"
```

### Запись в память
```python
def memory_write(session_id: str, action_type: str, details: dict):
    """Записать действие в память."""
    requests.post(f'{BASE}/hermes_memory', headers=HEADERS, json={
        'session_id': session_id,
        'action_type': action_type,
        'details': details
    })
```

### Чтение из памяти
```python
def memory_read(session_id: str, limit: int = 10) -> list:
    """Прочитать последние N записей для session_id."""
    r = requests.get(
        f'{BASE}/hermes_memory',
        params={
            'session_id': f'eq.{session_id}',
            'order': 'created_at.desc',
            'limit': limit
        },
        headers=HEADERS
    )
    return r.json() if r.status_code == 200 else []
```

### Поиск по типу действия
```python
def memory_find(action_type: str, limit: int = 20) -> list:
    """Найти все записи с данным action_type."""
    r = requests.get(
        f'{BASE}/hermes_memory',
        params={
            'action_type': f'eq.{action_type}',
            'order': 'created_at.desc',
            'limit': limit
        },
        headers=HEADERS
    )
    return r.json() if r.status_code == 200 else []
```

### Очистка старых записей
```python
def memory_cleanup(days: int = 30):
    """Удалить записи старше N дней."""
    r = requests.delete(
        f'{BASE}/hermes_memory',
        params={'created_at': f'lt.{days}days'},
        headers=HEADERS
    )
    return r.status_code == 204
```

## Когда использовать

**ЗАПИСЫВАЙ после каждого значимого шага:**
- `parse_complete` — парсинг завершён, details: `{count, source}`
- `clean_done` — очистка завершена, details: `{filtered, remaining}`
- `error` — ошибка, details: `{error, context}`
- `user_confirm` — пользователь подтвердил действие
- `dedup_done` — дедупликация, details: `{before, after, removed}`
- `transfer_done` — перенос в clients, details: `{count}`

**ЧИТАЙ перед началом многошаговой задачи:**
1. Прочитай последние 10 записей для текущего session_id
2. Восстанови: что уже сделано, какие ошибки были
3. Продолжай с того места где остановились

## Примеры action_type (из реальных сессий)

- `start` — начало задачи
- `analysis_done` — анализ данных
- `categorization_done` — категоризация
- `cleanup_start` / `cleanup_done` — очистка
- `dedup_done` — дедупликация
- `enrichment_done` — обогащение
- `fix_done` — исправление
- `final_classification_done` — финальная категоризация
- `error` — ошибка

## Создание таблицы (если не существует)

REST API Supabase **НЕ позволяет** создавать таблицы программно через service_role ключ.
**Единственный способ**: Supabase Dashboard → SQL Editor → New Query → Run

```sql
CREATE TABLE IF NOT EXISTS hermes_memory (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT,
    action_type TEXT,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_hermes_memory_session
ON hermes_memory(session_id, created_at DESC);
```

## Примечания
- Требуется `SUPABASE_SERVICE_KEY` из `~/.hermes/.env`
- Таблица уже создана (проверена 06.2026)
- Rate limit: ~100 req/s для бесплатного тарифа
- Не хранить большие объекты в details (JSONB лимит ~1MB)
