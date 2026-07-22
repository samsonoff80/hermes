# Contact Enrichment via web_search — 28-29.06.2026

## Контекст
Обогащение контактов (phone, email, website) для записей в `clean_clients` через `web_search`.

## Стратегия

### PDF-каталоги (ПРЕРЕФЕРРЕД)
- **В 170x эффективнее** web_search
- 4,344 компании за 30 секунд vs ~50 компаний/минуту через web_search
- Используй PyMuPDF + многопроходная очистка OCR

### web_search (для оставшихся)
Когда PDF не покрывает все компании — используй `web_search` через `execute_code`:

```python
from hermes_tools import web_search

# Запрос
q = f'"{name}" {country} контакты телефон email сайт'
res = web_search(q, limit=3)

# Извлечение
if res and res.get('success') and 'data' in res:
    txt = ' '.join(it.get('title','')+' '+it.get('description','') 
                   for it in res['data'].get('web',[])[:3])
    phone, email, website = extract(txt)
```

### Hit rate
- **PDF**: 99%+ email, 88% website, 100% описание
- **web_search**: 12-38% (зависит от страны/типа компании)
- **web_search для обогащения**: ~20% hit rate (только 1 из 5 записей получает контакт)

### Питфоллы web_search
1. **DuckDuckGo backend таймаутится** — нестабильно, иногда 50% ошибок
2. **Только execute_code** — web_search НЕ работает в subprocess/terminal
3. **Batчи по 25** — оптимально для таймаута 300с
4. **Sleep 0.1-0.15** между запросами
5. **Прогресс-файл** — сохраняй в `~/.hermes/enrich_progress.json` (НЕ в `/tmp`!)

### Прогресс-файл
**НЕ используй `/tmp/`** — файлы теряются при перезагрузке/очистке.
**Используй `~/.hermes/enrich_progress.json`** — персистентное хранилище.

```python
PROGRESS_FILE = os.path.expanduser("~/.hermes/enrich_progress.json")
progress = {'processed_offset': N, 'enriched_total': M}
```

### Фильтрация website
Исключай мусорные домены:
```python
BAD_DOMAINS = ['youtube','facebook','vk.com','2gis','yandex','google',
               'instagram','ok.ru','t.me','linkedin','wa.me','pinterest','tiktok']
```

### Нормализация телефона
```python
digits = re.sub(r'[^\d+]', '', phone_str)
if digits.startswith('8') and len(digits) == 11:
    phone = '+7' + digits[1:]
elif digits.startswith('7') and len(digits) == 11:
    phone = '+' + digits
```

## Результаты (29.06.2026)
- **PDF Prodexpo**: 4,344 компании → загружено в clean_clients
- **PDF Agroprodmash**: 1,410 компаний → +1,388 загружено (без дублей)
- **web_search**: +443 обогащённых (дополнительно к PDF)
- **Итого**: 2,500 записей в clean_clients (100% с контактами)
- **Беларусь**: полностью удалена (174 записи из БД + парсер обновлён)
