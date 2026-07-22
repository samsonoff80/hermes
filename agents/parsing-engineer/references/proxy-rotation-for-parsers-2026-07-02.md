# Прокси-ротация для парсеров

## Зачем нужна прокси-ротация
- **Блокировки**: Сайты блокируют IP после 50–100 запросов (HTTP 403/429).
- **Гео-ограничения**: Некоторые данные доступны только из определённых стран.
- **Таймауты**: Прямые запросы могут быть медленными или нестабильными.

## Конфигурация
### 1. Хранение прокси
- **Формат**: Список прокси в `.env`:
  ```
  PROXY_LIST=http://proxy1:port,http://proxy2:port,socks5://proxy3:port
  ```
- **Типы прокси**: HTTP, HTTPS, SOCKS5.
- **Аутентификация**: `http://user:pass@proxy:port`.

### 2. Ротация прокси
- **Метод**: Циклическая ротация через `itertools.cycle`.
- **Пример**:
  ```python
  import itertools, os
  proxies = itertools.cycle(os.getenv("PROXY_LIST", "").split(","))
  proxy = next(proxies)
  ```

### 3. Интеграция с инструментами
#### Requests
```python
import requests, os

proxies = {
    "http": os.getenv("HTTP_PROXY"),
    "https": os.getenv("HTTPS_PROXY")
}

response = requests.get("https://example.com", proxies=proxies, timeout=30)
```

#### Playwright
```python
from playwright.sync_api import sync_playwright

proxy = {"server": next(proxies)}
browser = p.chromium.launch(proxy=proxy)
```

#### Urllib
```python
import urllib.request

proxy_handler = urllib.request.ProxyHandler({"http": next(proxies)})
opener = urllib.request.build_opener(proxy_handler)
response = opener.open("http://example.com")
```

## Проверка работоспособности прокси
### 1. Скрипт проверки
```python
import requests, os

def check_proxy(proxy_url):
    try:
        proxies = {"http": proxy_url, "https": proxy_url}
        response = requests.get(
            "https://httpbin.org/ip",
            proxies=proxies,
            timeout=10
        )
        if response.status_code == 200:
            print(f"Proxy {proxy_url} works: {response.json()['origin']}")
            return True
        return False
    except Exception as e:
        print(f"Proxy {proxy_url} failed: {str(e)}")
        return False

# Проверка всех прокси
for proxy in os.getenv("PROXY_LIST", "").split(","):
    check_proxy(proxy)
```

### 2. Логирование
- Сохраняйте результаты проверки в `logs/proxy_check.log`.
- Формат: `дата | прокси | статус | IP`.

## Обработка ошибок
### 1. Таймауты и блокировки
- **Таймауты**: Повторять запрос с экспоненциальной задержкой (3 попытки).
- **Блокировки**: При HTTP 403/429 менять прокси и User-Agent.

### 2. Пример обработки
```python
import time, random

def fetch_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            proxy = next(proxies)
            response = requests.get(url, proxies={"http": proxy, "https": proxy}, timeout=30)
            if response.status_code == 200:
                return response
            elif response.status_code in [403, 429]:
                print(f"Blocked by {url}. Retrying with new proxy...")
                time.sleep(2 ** attempt)  # Экспоненциальная задержка
                continue
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            time.sleep(2 ** attempt)
    return None
```

## User-Agent ротация
- **Зачем**: Сайты блокируют запросы с дефолтным User-Agent.
- **Метод**: Ротация User-Agent вместе с прокси.
- **Пример**:
  ```python
  user_agents = [
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
      "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
  ]
  headers = {"User-Agent": random.choice(user_agents)}
  ```

## Прокси-провайдеры
| Провайдер       | Тип       | Цена       | Особенности                     |
|----------------|-----------|------------|---------------------------------|
| Luminati       | HTTP/SOCKS| $$$        | Высокая анонимность             |
| Smartproxy     | HTTP/HTTPS| $$         | Ротация IP                      |
| Oxylabs        | HTTP/HTTPS| $$$        | Гео-таргетинг                   |
| ProxyRack      | HTTP/SOCKS| $          | Дешёвые прокси                  |
| FreeProxyList  | HTTP      | Бесплатно  | Низкая стабильность             |

## Рекомендации
1. **Для массового парсинга**: Используйте платные прокси (Luminati, Oxylabs).
2. **Для тестирования**: Бесплатные прокси (FreeProxyList).
3. **Для AJAX-сайтов**: Playwright + прокси-ротация.
4. **Для статических сайтов**: Requests + прокси-ротация.

## Ссылки
- [Проверка прокси](scripts/check_proxies.py)
- [Бэкап прокси-листа](https://github.com/salesbot-hermes/hermes/blob/main/.env.example)