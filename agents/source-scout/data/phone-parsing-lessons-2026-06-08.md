# Парсинг телефонов с сайтов — уроки (обновлено 08.06.2026)

## Ключевой вывод: парсинг сайтов крайне неэффективен

Из ~1200 записей с website без телефона:
- **~720** (60%) — невалидный URL (`www` без домена, пустые строки)
- **~240** (20%) — домены без точки (`morsod`, `megatoys`, `foodmatik` и т.д.)
- **~225** (19%) — blacklist домены (torgbox, vk, facebook, rusprofile, telegram, wa.me)
- **~11-240** (1-20%) — реальные сайты (зависит от строгости фильтрации)

**Итог**: только ~10-15% website содержат реальные домены компаний.

## Распределение доменов без точки (244 записи)

52 уникальных домена без точки. Частые:
- `zamec`×9, `foodmatik`×7, `glass-decor`×7, `kmz`×7, `morsod`×6, `megatoys`×6

Большинство — мусор из парсинга. Скрипт v5 пробует добавлять `.ru`/`.com`/`.rf`/`.net`, но конверсия минимальна.

## Проблема Supabase SDK

`supabase.create_client()` **зависает** на длительных операциях (загрузка 1000+ записей).
**Решение**: использовать REST API через `requests` напрямую.

```python
# НЕ РАБОТАЕТ (зависает):
from supabase import create_client
sb = create_client(url, key)
sb.table("clients").select("*").execute()  # зависает на >500 записях

# РАБОТАЕТ:
import requests
r = requests.get(f"{SB_URL}/rest/v1/clients?select=*&limit=500&offset=0",
                 headers=headers, timeout=30)
data = r.json()
```

## Проблема Supabase REST API на больших ответах

REST API **таймаутится** при загрузке >600 строк с большим количеством колонок.
Использовать `limit=500` или меньше. Для `phone=not.is.null&limit=1000` — может таймаутиться.
Безопасный лимит: `limit=500`.

## Проблема артефактных телефонов

При массовом парсинге сайтов один номер может появиться у десятков компаний:
- `+78005500827` — номер хостинга/площадки, появился у **225** компаний
- Всегда проверять частоту телефонов после обогащения
- Если один номер у >3 компаний — скорее всего артефакт
- Обнулять (SET NULL), не удалять запись

## Чёрный список доменов

Обязательно фильтровать ДО парсинга:
- `torgbox.ru` — торговая площадка, не сайт компании
- `vk.com`, `facebook.com`, `instagram.com`, `ok.ru`, `t.me`, `telegram.me` — соцсети
- `rusprofile.ru`, `list-org.com`, `zachestnyibiznes.ru` — каталоги
- `wa.me` — WhatsApp ссылка
- `youtube.com`, `twitter.com` — медиа

## Чёрный список номеров

```python
BLACKLIST_PHONES = {
    '78005500827',  # Артефакт хостинга (225 раз)
    '88005500827',  # Тот же номер с 8
    '8005500827',   # Без кода страны
    '74951234567',  # Типичная заглушка
    '84951234567',
    '78005000601',  # Частый артефакт хостинга
    '88005000601',
    '78003500448',  # Ростелеком хостинг
    '88003500448',
}
```

## Валидация доменов

```python
from urllib.parse import urlparse

def normalize_url(url):
    if not url:
        return None
    url = url.strip()
    # Убрать мусор после пробела (кракозябры из парсинга)
    url = url.split()[0]
    if not url.startswith('http'):
        url = 'https://' + url
    return url.rstrip('/')

def is_valid_domain(url):
    """Проверяет что домен не пустой и не просто 'www'."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return bool(domain and domain != 'www')
    except:
        return False

def get_tlds_to_try(domain):
    """Для доменов без точки — пробует с разными TLD."""
    if '.' in domain:
        return [domain]
    return [f"{domain}.ru", f"{domain}.com", f"{domain}.rf", f"{domain}.net"]
```

## Таймаут на домен через signal.alarm

```python
import signal

old_handler = signal.signal(signal.SIGALRM, lambda s, f: (_ for _ in ()).throw(TimeoutError()))
signal.alarm(8)  # 8 секунд на весь домен (все страницы)
try:
    for suffix in ['', '/contacts', '/kontakty', '/contact']:
        resp = requests.get(f"https://{domain}{suffix}", timeout=3, ...)
        # ...
except TimeoutError:
    pass  # пропускать медленные сайты
finally:
    signal.alarm(0)
    signal.signal(signal.SIGALRM, old_handler)
```

## Вывод в background сессиях

`terminal(background=true)` не показывает stdout до завершения процесса.
- `flush=True` в `print()` помогает но не полностью
- Для длительных задач использовать `notify_on_complete=true`
- Прогресс-вывод каждые 25-50 записей — единственный способ отслеживать

## Результаты v5 (08.06.2026)

Скрипт `enrich_clients_phones_v5.py`:
- 131 валидный URL (после предфильтрации)
- 22 найденных телефона за ~3.5 минуты (до остановки)
- Скорость: ~0.4 rec/s (из-за таймаутов на домен)
- После очистки артефактов и повторного запуска: 581 телефон (с 518)

## Рекомендация

Для массового обогащения телефонов использовать **внешние API** (DaData платный findById, FocusAPI) по ИНН/OGRN, а не парсинг сайтов. Парсинг сайтов — только для точечного поиска по известным реальным доменам.

## Скрипты

- `scripts/enrich_clients_phones_v5.py` — **текущая рекомендуемая версия** (REST API, blacklist, таймауты, tel: приоритет)
- `scripts/enrich_clients_phones_v3.py` — старая версия (Supabase SDK, зависает)
- `scripts/clean_artifact_phones.py` — очистка артефактных номеров

## Архитектура v5

```
normalize_url() → is_valid_domain() → is_blacklisted_domain() → get_phone()
                                                                   ↓
                                                              signal.alarm(8)
                                                                   ↓
                                                          get_phone_from_domain()
                                                                   ↓
                                                    tel: links (приоритет 1)
                                                    regex text (приоритет 2)
                                                    blacklist check
```
