# Обработка ошибок API

## Логирование ошибок

Логируй все ошибки API в `enrichment.log`:

```
2026-07-01 13:44:22 [ERROR] Enrichment failed for ООО "Ромашка": 400 Not enough credits
2026-07-01 13:44:23 [WARNING] Switching to fallback for ООО "Ромашка"
```

## Автоматическое переключение на fallback

При ошибках `400` или `429` переключайся на fallback-стратегии:

```python
def handle_api_error(error: str, company: str) -> str:
    """Обрабатывает ошибки API и переключается на fallback."""
    if "400" in error or "429" in error:
        logging.warning(f"Switching to fallback for {company}")
        return "fallback"
    raise Exception(f"Enrichment failed: {error}")
```

## Retry-стратегия для временных ошибок

```python
import time
from typing import Callable

def retry_api_call(api_func: Callable, max_retries: int = 3, delay: int = 2) -> dict:
    """Повторяет запрос к API при временных ошибках."""
    for attempt in range(max_retries):
        try:
            return api_func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(delay * (attempt + 1))
```