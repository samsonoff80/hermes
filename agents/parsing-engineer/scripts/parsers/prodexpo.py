"""Парсер Продэкспо 2022-2026 (5 лет)"""
import requests, re, json, time, os
from bs4 import BeautifulSoup
from datetime import datetime

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

# 5 лет, две платформы
EXHIBITIONS = [
    {"year": 2022, "platform": "old", "wyst_id": "207", "url": "https://catalog.expocentr.ru/catalog.php?wyst_id=207"},
    {"year": 2023, "platform": "new", "uuid": "d3a90aa7-bdf4-11eb-80cc-a0d3c1fab97f"},
    {"year": 2024, "platform": "new", "uuid": "97cfb9c0-dfee-11ec-80cd-a0d3c1fab97f"},
    {"year": 2025, "platform": "new", "uuid": "b5cf5aaa-3c26-11ee-80ce-a0d3c1fab97f"},
    {"year": 2026, "platform": "new", "uuid": "870c9c18-e84b-11ef-80ce-a0d3c1fab97f"},
]

def get_list_new(uuid):
    """Список с новой платформы"""
    url = f"https://icatalog.expocentr.ru/ru/exhibitions/{uuid}/list"
    r = requests.get(url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, 'html.parser')
    companies = []
    for row in soup.select("table tbody tr"):
        name_cell = row.select_one("td:nth-child(1) a")
        country_cell = row.select_one("td:nth-child(2)")
        if name_cell:
            companies.append({
                "name": name_cell.get_text(strip=True),
                "card_url": name_cell.get("href"),
                "country": country_cell.get_text(strip=True) if country_cell else ""
            })
    return companies

def get_card_new(card_url):
    """Карточка с новой платформы"""
    full_url = f"https://icatalog.expocentr.ru{card_url}" if card_url.startswith("/") else card_url
    r = requests.get(full_url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, 'html.parser')
    data = {}
    for dt in soup.find_all('dt'):
        key = dt.get_text(strip=True).rstrip(':')
        dd = dt.find_next('dd')
        value = dd.get_text(strip=True) if dd else ""
        if 'Страна' in key: data['country'] = value
        elif 'Город' in key: data['city'] = value
        elif 'Адрес' in key: data['address'] = value
        elif 'Телефон' in key: data['phone'] = value
        elif 'Сайт' in key: data['website'] = value
        elif 'E-mail' in key: data['email'] = value
        elif 'Описание' in key: data['description'] = value
        elif 'Рубрики' in key: data['categories'] = value
    return data

def get_list_old(wyst_id):
    """Список со старой платформы (2022)"""
    url = f"https://catalog.expocentr.ru/catalog.php?wyst_id={wyst_id}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, 'html.parser')
    companies = []
    for row in soup.select("table tr"):
        cells = row.find_all('td')
        if len(cells) >= 3:
            name_cell = cells[0].find('a')
            if name_cell:
                companies.append({
                    "name": name_cell.get_text(strip=True),
                    "card_url": name_cell.get("href"),
                    "country": cells[2].get_text(strip=True) if len(cells) > 2 else ""
                })
    return companies

def get_card_old(card_url):
    """Карточка со старой платформы"""
    full_url = f"https://catalog.expocentr.ru/{card_url}" if not card_url.startswith("http") else card_url
    r = requests.get(full_url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, 'html.parser')
    data = {}
    text = soup.get_text()
    # Страна
    country_match = re.search(r'Страна:\s*(.+)', text)
    if country_match: data['country'] = country_match.group(1).strip()
    # Город
    city_match = re.search(r'Город:\s*(.+)', text)
    if city_match: data['city'] = city_match.group(1).strip()
    # Телефон
    phone_match = re.search(r'(?:\+7|8)\s*\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}', text)
    if phone_match: data['phone'] = phone_match.group()
    # Email
    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    if email_match: data['email'] = email_match.group()
    # Сайт
    site_match = re.search(r'https?://[^\s<>"]+', text)
    if site_match: data['website'] = site_match.group()
    return data

def run_year(exh, limit=None):
    """Парсинг одного года"""
    print(f"\n{'='*50}")
    print(f"Продэкспо {exh['year']} ({exh['platform']})")
    
    if exh['platform'] == 'new':
        companies = get_list_new(exh['uuid'])
    else:
        companies = get_list_old(exh['wyst_id'])
    
    print(f"Найдено: {len(companies)} компаний")
    
    results = []
    total = limit or len(companies)
    
    for i, c in enumerate(companies[:total]):
        print(f"  [{i+1}/{total}] {c['name'][:40]}...")
        try:
            if exh['platform'] == 'new':
                card = get_card_new(c['card_url'])
            else:
                card = get_card_old(c['card_url'])
            results.append({**c, **card, "source": f"prodexpo_{exh['year']}", "parsed_at": datetime.now().isoformat()})
        except Exception as e:
            print(f"    ❌ {e}")
            results.append(c)
        time.sleep(0.3)
    
    # Сохраняем
    out_file = f"data/prodexpo_{exh['year']}.json"
    with open(out_file, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    with_phone = sum(1 for r in results if r.get('phone'))
    with_email = sum(1 for r in results if r.get('email'))
    with_site = sum(1 for r in results if r.get('website'))
    print(f"✅ {out_file}: {len(results)} компаний (📞{with_phone} 📧{with_email} 🌐{with_site})")
    return results

def run(limit=None):
    """Все годы"""
    all_results = []
    for exh in EXHIBITIONS:
        results = run_year(exh, limit)
        all_results.extend(results)
    
    # Общий файл
    with open("data/prodexpo_all.json", "w") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    total = len(all_results)
    with_phone = sum(1 for r in all_results if r.get('phone'))
    print(f"\n{'='*50}")
    print(f"ВСЕГО: {total} компаний за 5 лет")
    print(f"📞 С телефоном: {with_phone} ({with_phone*100//total}%)")
    print(f"📧 С email: {sum(1 for r in all_results if r.get('email'))}")
    print(f"🌐 С сайтом: {sum(1 for r in all_results if r.get('website'))}")
    
    return all_results

if __name__ == "__main__":
    run(limit=3)  # Тест: по 3 компании с года
