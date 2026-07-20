#!/usr/bin/env python3
"""Health Checker — проверка провайдеров при старте."""
import asyncio, httpx, logging, time

logger = logging.getLogger("consilium.health")

async def check_provider(name, base_url, key, keyless=False):
    if keyless or not base_url:
        return True
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{base_url}/models",
                headers={"Authorization": f"Bearer {key}"} if key else {})
            return r.status_code == 200
    except:
        return False

async def check_all_providers(providers):
    start = time.time()
    tasks = []
    for p in providers:
        key = p.get("keys", [None])[0] if p.get("keys") else None
        tasks.append(check_provider(p["name"], p.get("base_url",""), key, p.get("keyless", False)))
    results = await asyncio.gather(*tasks)
    alive = sum(results)
    logger.info(f"🏥 Health check: {alive}/{len(providers)} alive ({time.time()-start:.1f}s)")
    return results
