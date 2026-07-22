"""Matcher — сравнение с МойСклад"""
import os, sys, re, requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cleaners import clean_name, extract_country_city, is_glaze_group
from providers import consilium_ask

def get_moysklad_clients():
    """Выгрузка клиентов из МойСклад с тегом 'глазури'"""
    from dotenv import load_dotenv
    load_dotenv(os.path.expanduser("~/.hermes/.env"))
    login = os.getenv("MOYSKLAD_LOGIN")
    password = os.getenv("MOYSKLAD_PASSWORD")
    if not login or not password:
        print("⚠️ Нет доступа к МойСклад")
        return []
    
    auth = requests.auth.HTTPBasicAuth(login, password)
    base = "https://api.moysklad.ru/api/remap/1.2"
    clients = []
    offset = 0
    
    while True:
        r = requests.get(f"{base}/entity/counterparty", auth=auth,
            params={"filter": "tags~глазури", "limit": 100, "offset": offset,
                    "expand": "contactpersons"})
        if r.status_code != 200:
            break
        rows = r.json().get("rows", [])
        if not rows:
            break
        for row in rows:
            country, city = extract_country_city(row.get("legalAddress", ""))
            clients.append({
                "moysklad_id": row["id"],
                "legal_title": row.get("legalTitle", ""),
                "name_clean": clean_name(row.get("legalTitle", "")),
                "inn": row.get("inn", ""),
                "country": country,
                "city": city,
                "tags": row.get("tags", []),
                "phone": row.get("phone", ""),
                "email": row.get("email", ""),
            })
        offset += 100
        if len(rows) < 100:
            break
    
    print(f"📦 МойСклад: {len(clients)} клиентов с тегом 'глазури'")
    return clients

async def run_matcher(session, our_clients, stats):
    """Сравнение нашей базы с МойСклад"""
    print("\n=== ЭТАП 4: MATCHER ===")
    ms_clients = get_moysklad_clients()
    if not ms_clients:
        print("⚠️ Пропускаем (нет доступа к МойСклад)")
        return our_clients
    
    duplicates = 0
    for c in our_clients:
        c.name_clean = clean_name(c.name_clean or c.legal_title or "")
        stats.matcher_compared += 1
        
        for ms in ms_clients:
            # Точное совпадение
            if c.name_clean == ms["name_clean"] and c.country == ms["country"]:
                c.is_duplicate = True
                c.duplicate_of = ms["moysklad_id"]
                duplicates += 1
                break
            
            # Совпадение ИНН
            if c.inn and ms["inn"] and c.inn == ms["inn"]:
                c.is_duplicate = True
                c.duplicate_of = ms["moysklad_id"]
                duplicates += 1
                break
            
            # Разница 1-2 символа → AI
            if c.country == ms["country"]:
                len_diff = abs(len(c.name_clean) - len(ms["name_clean"]))
                if len_diff <= 2:
                    from Levenshtein import distance
                    if distance(c.name_clean, ms["name_clean"]) <= 2:
                        prompt = f"Это одна компания?\n1: {c.name_clean}\n2: {ms['name_clean']}\nСтрана: {c.country}\nОтветь ДА или НЕТ"
                        result = await consilium_ask(session, prompt)
                        if result.get("best", "").strip().upper() == "ДА":
                            c.is_duplicate = True
                            c.duplicate_of = ms["moysklad_id"]
                            duplicates += 1
                            break
    
    stats.matcher_duplicates = duplicates
    print(f"✅ Matcher завершён: {duplicates} дублей из {stats.matcher_compared}")
    return our_clients
