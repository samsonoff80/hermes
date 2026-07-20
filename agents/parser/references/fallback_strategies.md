# Fallback-стратегии для обогащения

## Извлечение домена из `email`

```python
def extract_domain_from_email(email):
    """Извлекает домен из email-адреса."""
    if not email or '@' not in email:
        return None
    return email.split('@')[-1]
```

## Извлечение домена из социальных сетей

```python
def extract_domain_from_social(url):
    """Извлекает домен из URL социальных сетей."""
    if not url:
        return None
    domain = url.split('/')[2]  # Убираем 'https://' и путь
    return domain if '.' in domain else None
```

## Логирование ошибок и переключение на fallback

```python
import logging
from typing import Optional

def log_and_switch_to_fallback(error: str, company: str, source: str = "Serper API") -> Optional[str]:
    """Логирует ошибку и переключается на fallback-стратегию."""
    logging.error(f"Enrichment failed for {company}: {error}")
    if "Not enough credits" in error or "429" in error:
        logging.warning(f"Switching to fallback for {company}")
        return "fallback"
    return None
```

## Пример использования fallback-стратегий

```python
def enrich_website(company_data: dict) -> Optional[str]:
    """Обогащает поле `website` с использованием fallback-стратегий."""
    # 1. Пробуем Serper API
    website = fetch_from_serper(company_data)
    if website:
        return website

    # 2. Fallback: извлечение из email
    if company_data.get('email'):
        return extract_domain_from_email(company_data['email'])

    # 3. Fallback: извлечение из социальных сетей
    for field in ['twitter_url', 'linkedin_url', 'facebook_url']:
        if company_data.get(field):
            return extract_domain_from_social(company_data[field])

    return None
```