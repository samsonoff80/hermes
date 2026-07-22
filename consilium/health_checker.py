#!/usr/bin/env python3
"""Health Checker — прогрев и проверка провайдеров при старте.

Исправлено:
- URL Cloudflare содержит плейсхолдер {ACCOUNT_ID}; запрос по нему уходил
  на несуществующий адрес и провайдер всегда числился мёртвым.
- Провайдеры без /models (has_api=False) проверять этим способом нельзя —
  раньше они молча помечались живыми или мёртвыми наугад.
- Голый `except:` глотал в том числе KeyboardInterrupt.
- Результат нигде не использовался: lifespan просто писал строку в лог.
"""
import asyncio
import os
import time
import logging
from typing import List

import httpx

logger = logging.getLogger("consilium.health")

CHECK_TIMEOUT = 5.0


async def check_provider(client: httpx.AsyncClient, provider: dict) -> bool:
    name = provider.get("name", "?")
    base_url = provider.get("base_url", "")
    if not base_url:
        return False

    # Провайдеры без OpenAI-совместимого /models не проверяем сетевым запросом:
    # отсутствие эндпоинта не означает, что провайдер мёртв.
    if provider.get("has_api") is False or "{ACCOUNT_ID}" in base_url:
        logger.info(f"🏥 {name}: /models недоступен, проверка пропущена")
        return True

    keys = provider.get("keys") or []
    key = keys[0] if keys else None
    if not key and not provider.get("keyless", False):
        logger.warning(f"🏥 {name}: нет ключей")
        return False

    headers = {"Authorization": f"Bearer {key}"} if key else {}
    try:
        r = await client.get(f"{base_url}/models", headers=headers, timeout=CHECK_TIMEOUT)
    except (httpx.HTTPError, OSError) as e:
        logger.warning(f"🏥 {name}: ❌ {type(e).__name__}")
        return False

    if r.status_code == 200:
        logger.info(f"🏥 {name}: ✅ OK")
        return True
    if r.status_code == 429:
        logger.warning(f"🏥 {name}: ⚠️ 429 (rate limited, ключи считаем живыми)")
        return True
    logger.warning(f"🏥 {name}: ❌ HTTP {r.status_code}")
    return False


async def check_all_providers(providers: list) -> List[bool]:
    if os.getenv("CONSILIUM_SKIP_HEALTHCHECK", "").lower() in ("1", "true", "yes"):
        logger.info("🏥 Health check отключён через CONSILIUM_SKIP_HEALTHCHECK")
        return [True] * len(providers)

    start = time.time()
    async with httpx.AsyncClient(timeout=CHECK_TIMEOUT) as client:
        results = await asyncio.gather(
            *(check_provider(client, p) for p in providers),
            return_exceptions=True,
        )
    normalized = [bool(r) if not isinstance(r, BaseException) else False for r in results]
    logger.info(f"🏥 Health check: {sum(normalized)}/{len(providers)} живых "
                f"({time.time()-start:.1f}s)")
    return normalized
