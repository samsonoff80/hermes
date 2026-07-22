"""Enricher — обогащение ИНН, телефонами, сайтами, email"""
import os, sys, asyncio, aiohttp, re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from providers import consilium_ask
from cleaners import normalize_country

PROXY = "https://proton-proxy.onrender.com/proxy?url="
DADATA_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party"

async def enrich_dadata(session, client, api_key):
    """Поиск ИНН через DaData"""
    headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}
    data = {"query": client.name_clean}
    try:
        async with session.post(DADATA_URL, json=data, headers=headers,
                                timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status == 200:
                j = await r.json()
                if j.get("suggestions"):
                    s = j["suggestions"][0]["data"]
                    client.inn = s.get("inn")
                    client.legal_address = s.get("address", {}).get("value", "")
                    client.country = normalize_country(s.get("address", {}).get("data", {}).get("country", "")) or client.country
                    return True
    except:
        pass
    return False

async def enrich_sbis(session, client):
    """Поиск телефона через sbis.ru по ИНН"""
    if not client.inn:
        return False
    url = f"https://sbis.ru/contragents/{client.inn}"
    text = await fetch_url(session, url)
    if text:
        phones = re.findall(r'(?:\+7|8)\s*\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}', text)
        if phones:
            client.phone = phones[0]
            return True
    return False

async def search_website_duckduckgo(session, client):
    """Поиск сайта через DuckDuckGo"""
    query = f"{client.name_clean} {client.country} официальный сайт"
    url = f"https://html.duckduckgo.com/html/?q={query}"
    text = await fetch_url(session, url)
    if text:
        urls = re.findall(r'https?://[^\s<>"]+', text)
        for u in urls[:10]:
            if any(d in u for d in ['.ru', '.kz', '.uz', '.az', '.am', '.kg', '.tj', '.tm', '.ge', '.com']):
                if not any(b in u for b in ['vk.com', 'facebook', 'instagram', 'youtube', 't.me', '2gis']):
                    client.website = u
                    return True
    return False

async def fetch_url(session, url, timeout=15):
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            if r.status == 200:
                return await r.text()
    except:
        pass
    return None

async def run_enricher(session, clients, stats):
    """Главный метод Enricher"""
    print("\n=== ЭТАП 2: ENRICHER ===")
    from dotenv import load_dotenv
    load_dotenv(os.path.expanduser("~/.hermes/.env"))
    dadata_key = os.getenv("DADATA_TOKEN", "")
    
    for i, c in enumerate(clients):
        if i % 100 == 0:
            print(f"  Прогресс: {i}/{len(clients)} (+{stats.enrich_phones} тел, +{stats.enrich_inns} ИНН)")
        
        if not c.inn and dadata_key:
            await enrich_dadata(session, c, dadata_key)
            if c.inn:
                stats.enrich_inns += 1
        
        if not c.phone and c.inn:
            await enrich_sbis(session, c)
            if c.phone:
                stats.enrich_phones += 1
        
        if not c.website:
            await search_website_duckduckgo(session, c)
            if c.website:
                stats.enrich_websites += 1
        
        await asyncio.sleep(0.3)
    
    print(f"✅ Enricher завершён: +{stats.enrich_inns} ИНН, +{stats.enrich_phones} тел, +{stats.enrich_websites} сайтов")
    return clients
