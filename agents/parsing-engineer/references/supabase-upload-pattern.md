# Supabase Upload Template (обновлено 19.06.2026)

## Рабочий паттерн загрузки через urllib

```python
import urllib.request, json, os, time

supabase_url = ''
supabase_key = ''
with open('/home/khadas/.hermes/.env', 'r') as f:
    for line in f:
        line = line.strip()
        if line.startswith('SUPABASE_URL='):
            supabase_url = line.split('=', 1)[1].strip().strip('"').strip("'")
        elif line.startswith('SUPABASE_SERVICE_KEY='):
            supabase_key = line.split('=', 1)[1].strip().strip('"').strip("'")

def upload_batch(batch, table='raw_parsed_data'):
    url = supabase_url + '/rest/v1/' + table
    data = json.dumps(batch, ensure_ascii=False).encode('utf-8')
    headers = {
        'apikey': supabase_key,
        'Authorization': 'Bearer ' + supabase_key,
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal',
    }
    req = urllib.request.Request(url, data=data, method='POST', headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return True, resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ''
        return False, str(e.code) + ': ' + body[:200]

batch_size = 50
for i in range(0, len(records), batch_size):
    batch = records[i:i+batch_size]
    success, msg = upload_batch(batch)
    if not success:
        print('Error: ' + msg)
    time.sleep(0.05)
```

## Критические заметки

1. **НЕ используйте curl** - возвращает 401 даже с правильными ключами
2. **НЕ используйте requests.post()** - может зависать
3. **Integer поля** (source_year) не принимают пустую строку - пропускайте ключ
4. **Нормализуйте записи** - все объекты в батче должны иметь одинаковый набор ключей
5. **Проверяйте данные ДО загрузки** - raw_parsed_data может быть пустой при наличии локальных JSON
