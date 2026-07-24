# Диагностика ключей Serper API

## Проверка ключа через `curl`

```bash
curl -X POST "https://google.serper.dev/search" \
-H "X-API-KEY: <YOUR_KEY>" \
-H "Content-Type: application/json" \
-d '{"q": "test", "gl": "ru", "hl": "ru"}'
```

### Ожидаемые ответы:
- **200 OK**: Ключ валиден. Пример ответа:
  ```json
  {
    "searchParameters": {"q": "test", "gl": "ru", "hl": "ru"},
    "organic": [{"title": "...", "link": "..."}]
  }
  ```

- **400 Bad Request**:
  - `{"message":"Not enough credits","statusCode":400}` → Ключ заблокирован из-за нехватки кредитов.
  - `{"message":"Invalid API key","statusCode":401}` → Неверный ключ.

### Действия при ошибках:
1. **`Not enough credits`**: Запросить новый ключ у владельца.
2. **`Invalid API key`**: Проверить корректность ключа в `temp_keys.json`.

---

## Хранение ключей
- **Файл**: `~/.hermes/skills/consilium/temp_keys.json`
- **Формат**:
  ```json
  {
    "keys": {
      "SERPER_API_KEY": {
        "current": "<KEY>",
        "status": "active",
        "limit": "2500 запросов/день"
      }
    }
  }
  ```