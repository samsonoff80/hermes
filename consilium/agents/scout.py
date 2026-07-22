"""Scout — поиск компаний по всем источникам"""
import os, sys, asyncio, aiohttp, json, re, time
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import Client, TARGET_COUNTRIES

PROXY = "https://proton-proxy.onrender.com/proxy?url="

# Источники: (название, url, страна, метод)
SOURCES = [
    # Россия — каталоги (requests)
    ("productcenter_ru", "https://productcenter.ru/producers/catalog-konditierskiie-izdieliia-427", "Россия", "catalog"),
    ("fabricators_ru", "https://fabricators.ru/proizvodstvo/konditerskie-fabriki", "Россия", "catalog"),
    ("foodmarkets_ru", "https://foodmarkets.ru/firms/", "Россия", "catalog"),
    ("foodretail_ru", "https://foodretail.ru/litecat", "Россия", "catalog"),
    ("foodsuppliers_ru", "https://foodsuppliers.ru/", "Россия", "catalog"),
    
    # Казахстан
    ("factories_kz", "https://factories.kz/producers/pischevaya-promyshlennost", "Казахстан", "catalog"),
    ("flagma_kz", "https://flagma.kz/en/companies/foodstuffs-companies/", "Казахстан", "catalog"),
    
    # Узбекистан
    ("flagma_uz", "https://flagma.uz/ru/kompanii", "Узбекистан", "catalog"),
    
    # Кыргызстан
    ("flagma_kg", "https://flagma-kg.com/", "Кыргызстан", "catalog"),
]

EXHIBITIONS = [
    ("agroprodmash", "https://icatalog.expocentr.ru/ru/exhibitions/b67ac0af-40d1-11ee-80ce-a0d3c1fab97f/alphabet/А?page=1", "Россия"),
    ("worldfood_moscow", "https://10times.com/world-food-moscow/exhibitors", "Россия"),
    ("worldfood_istanbul", "https://worldfood-istanbul.com/en/exhibitor-list", "Турция"),
    ("gulfood", "https://exhibitors.gulfood.com/gulfood-2026/Exhibitors", "ОАЭ"),
]

async def fetch_url(session, url, timeout=15):
    """Запрос с fallback через прокси"""
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            if r.status == 200:
                return await r.text()
    except:
        pass
    try:
        async with session.get(f"{PROXY}{url}", headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            if r.status == 200:
                return await r.text()
    except:
        pass
    return None

def parse_name_country_from_html(html, source_name):
    """Простой парсинг названий из HTML"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    clients = []
    text = soup.get_text()
    lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 3]
    for line in lines[:500]:
        if any(kw in line.lower() for kw in ['кондитер', 'шоколад', 'молоч', 'хлеб', 'пекар', 'орех', 'сухофрукт', 'морожен']):
            clients.append({"name": line[:120], "source": source_name})
    return clients

async def scout_source(session, name, url, country, method):
    """Сбор с одного источника"""
    print(f"  🔍 {name}...")
    html = await fetch_url(session, url)
    if html:
        clients = parse_name_country_from_html(html, name)
        for c in clients:
            c["country"] = country
        print(f"    ✅ {len(clients)} компаний")
        return clients
    else:
        print(f"    ❌ недоступен")
        return []

async def run_scout(session, stats):
    """Главный метод Scout"""
    print("\n=== ЭТАП 1: SCOUT ===")
    all_clients = []
    
    # Каталоги
    for name, url, country, method in SOURCES:
        clients = await scout_source(session, name, url, country, method)
        all_clients.extend(clients)
        await asyncio.sleep(0.5)
    
    # Выставки
    for name, url, country in EXHIBITIONS:
        clients = await scout_source(session, name, url, country, "exhibition")
        all_clients.extend(clients)
        await asyncio.sleep(0.5)
    
    # Сохраняем в Supabase
    if all_clients:
        from dotenv import load_dotenv
        load_dotenv(os.path.expanduser("~/.hermes/.env"))
        from supabase import create_client
        sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
        for batch in [all_clients[i:i+50] for i in range(0, len(all_clients), 50)]:
            data = [{
                "name_clean": c.get("name", "")[:200],
                "country": c.get("country", ""),
                "source": c.get("source", ""),
                "group_tag": "Не определено"
            } for c in batch]
            try:
                sb.table("clean_clients").upsert(data, on_conflict="moysklad_id").execute()
            except:
                pass
    
    stats.scout_found = len(all_clients)
    print(f"\n✅ Scout завершён: {len(all_clients)} компаний")
    return all_clients
