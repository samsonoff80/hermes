#!/usr/bin/env python3
"""
Универсальный парсер каталогов. Читает конфиг из Supabase source_profiles и парсит сайты.

Архитектура:
  Consilium Brain → source_profiles (Supabase) → parse_catalogs.py → raw_parsed_data

Использование:
  python3 parse_catalogs.py --list         # список всех профилей
  python3 parse_catalogs.py --source Продэкспо 2025
  python3 parse_catalogs.py --all          # все профили
  python3 parse_catalogs.py --url URL      # найти профиль по URL
"""

import os
import sys
import json
import re
import argparse
import urllib.request
import urllib.error
from datetime import datetime, date

# Добавляем путь к проекту
sys.path.insert(0, os.path.expanduser("~/.hermes"))
from dotenv import load_dotenv
load_dotenv(os.path.expanduser("~/.hermes/.env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# ─── Supabase helpers ───────────────────────────────────────────

def sb_get(table, params=None, page_size=500):
    """Получить все записи из Supabase с пагинацией."""
    all_data = []
    offset = 0
    while True:
        p = dict(params or {})
        p["limit"] = str(page_size)
        p["offset"] = str(offset)
        p["order"] = "id.asc"
        from urllib.parse import quote
        url = f"{SUPABASE_URL}/rest/v1/{table}?" + "&".join(f"{k}={quote(str(v), safe='')}" for k, v in p.items())
        req = urllib.request.Request(url)
        req.add_header("apikey", SUPABASE_KEY)
        req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read().decode())
            if not data:
                break
            all_data.extend(data)
            offset += page_size
            if len(data) < page_size:
                break
        except Exception as e:
            print(f"[WARN] sb_get {table}: {e}")
            break
    return all_data


def sb_upsert(table, data, conflict="id"):
    """Upsert в Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?on_conflict={conflict}"
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=representation")
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"[WARN] sb_upsert {table}: {e.code} {body[:200]}")
        return None


def sb_update(table, record_id, data):
    """Обновить запись по ID."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?id=eq.{record_id}"
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="PATCH")
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=representation")
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"[WARN] sb_update {table}: {e.code} {body[:200]}")
        return None


# ─── Profile loading ────────────────────────────────────────────

def load_profiles(source_name=None, url=None):
    """Загрузить профили из source_profiles."""
    params = {}
    if source_name:
        params["source_name"] = f"eq.{source_name}"
    if url:
        params["url"] = f"eq.{url}"
    
    profiles = sb_get("source_profiles", params)
    
    # Парсим selectors (могут быть строкой или dict)
    for p in profiles:
        if isinstance(p.get("selectors"), str):
            try:
                p["selectors"] = json.loads(p["selectors"])
            except:
                p["selectors"] = {}
        if isinstance(p.get("detail_selectors"), str):
            try:
                p["detail_selectors"] = json.loads(p["detail_selectors"])
            except:
                p["detail_selectors"] = {}
    
    return profiles


def list_profiles():
    """Вывести список всех профилей."""
    profiles = load_profiles()
    if not profiles:
        print("Нет профилей в source_profiles")
        return
    
    print("\n{:<30} {:<12} {:<12} {:<10} {}".format("Источник", "Метод", "Структура", "Пагинация", "URL"))
    print("─" * 120)
    for p in profiles:
        name = p.get('source_name','?') or '?'
        method = p.get('parsing_method','?') or '?'
        struct = p.get('data_structure','?') or '?'
        pag = p.get('pagination_type') or 'нет'
        url = p.get('url','?') or '?'
        print("{:<30} {:<12} {:<12} {:<10} {}".format(name[:30], method[:12], struct[:12], pag[:10], url))


# ─── HTTP fetcher ───────────────────────────────────────────────

def fetch_page(url, method="requests", headers=None, timeout=15):
    """Получить HTML страницы."""
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru,en;q=0.9,tr;q=0.5",
    }
    if headers:
        default_headers.update(headers)
    
    if method == "requests":
        try:
            import requests
            resp = requests.get(url, headers=default_headers, timeout=timeout, allow_redirects=True)
            return resp.text
        except Exception as e:
            print(f"[ERROR] fetch_page: {e}")
            return None
    else:
        req = urllib.request.Request(url, headers=default_headers)
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
            return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            print(f"[ERROR] fetch_page: {e}")
            return None


# ─── Table parser ───────────────────────────────────────────────

def parse_table_page(html, selectors, base_url):
    """Парсинг табличной структуры."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("[ERROR] beautifulsoup4 не установлен: pip install beautifulsoup4")
        return []
    
    soup = BeautifulSoup(html, "html.parser")
    records = []
    
    # Основные селекторы
    name_sel = selectors.get("name", "")
    country_sel = selectors.get("country", "")
    card_url_sel = selectors.get("card_url", "")
    
    # Находим строки таблицы
    if card_url_sel:
        rows = soup.select(f"tr:has({card_url_sel})")
    else:
        rows = soup.select("tr")
    
    if not rows:
        rows = soup.select("table tr")
    
    for row in rows:
        cells = row.select("td")
        if len(cells) < 2:
            continue
        
        record = {}
        
        # Название
        if name_sel:
            el = row.select_one(name_sel)
            if el:
                record["name"] = el.get_text(strip=True)
                # Ссылка если есть <a> внутри
                a_tag = el.find("a")
                if a_tag and a_tag.get("href"):
                    record["url"] = a_tag["href"] if a_tag["href"].startswith("http") else base_url + a_tag["href"]
        
        # Страна
        if country_sel:
            el = row.select_one(country_sel)
            if el:
                record["country"] = el.get_text(strip=True)
        
        # Если нет селекторов — эвристики
        if not record.get("name"):
            text_cells = [c.get_text(strip=True) for c in cells if c.get_text(strip=True)]
            if text_cells:
                record["name"] = text_cells[0]
                if len(text_cells) > 1:
                    record["country"] = text_cells[1]
        
        if record.get("name"):
            record["source_url"] = base_url
            records.append(record)
    
    return records


# ─── Card parser ────────────────────────────────────────────────

def parse_card_page(html, selectors, base_url):
    """Парсинг карточной структуры (div-карточки)."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("[ERROR] beautifulsoup4 не установлен")
        return []
    
    soup = BeautifulSoup(html, "html.parser")
    records = []
    
    # Селектор карточки
    card_sel = selectors.get("card", "")
    name_sel = selectors.get("name", "")
    
    if card_sel:
        cards = soup.select(card_sel)
    elif name_sel:
        cards = soup.select(name_sel)
        # Если селектор указывает на элемент внутри карточки
        # — ищем родительский контейнер
    else:
        # Эвристика: ищем повторяющиеся div с текстом
        cards = soup.select("div.company, div.item, article, .card")
    
    for card in cards:
        record = {}
        
        if name_sel:
            el = card.select_one(name_sel) if hasattr(card, 'select_one') else None
            if el:
                record["name"] = el.get_text(strip=True)
        else:
            # Берём первый текст
            text = card.get_text(strip=True)[:200]
            if text:
                # Первая строка = название
                lines = text.split("\n")
                record["name"] = lines[0].strip()
        
        if record.get("name"):
            record["source_url"] = base_url
            records.append(record)
    
    return records


# ─── SPA/JS parser (placeholder) ───────────────────────────────

def parse_spa_page(url, selectors):
    """Для SPA нужно использовать Playwright — заглушка."""
    print(f"[WARN] SPA парсинг требует Playwright: {url}")
    print("[WARN] Используйте browser tool для SPA сайтов")
    return []


# ─── Detail page parser ─────────────────────────────────────────

def fetch_details(records, profile, base_url):
    """Загрузить детали со страницы компании."""
    if not profile.get("needs_detail_page"):
        return records
    
    detail_selectors = profile.get("detail_selectors", {})
    if not detail_selectors:
        return records
    
    # Ограничиваем количество детальных страниц
    max_details = 50
    for i, record in enumerate(records[:max_details]):
        detail_url = record.get("url", "")
        if not detail_url:
            continue
        
        if not detail_url.startswith("http"):
            detail_url = base_url.rstrip("/") + "/" + detail_url.lstrip("/")
        
        html = fetch_page(detail_url, method=profile.get("parsing_method", "requests"))
        if not html:
            continue
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            
            for field, sel in detail_selectors.items():
                el = soup.select_one(sel) if hasattr(soup, 'select_one') else None
                if el:
                    record[field] = el.get_text(strip=True)
                    # Если это ссылка
                    a_tag = el.find("a") if hasattr(el, 'find') else None
                    if a_tag and a_tag.get("href"):
                        record[field] = a_tag["href"]
        except Exception as e:
            print(f"[WARN] Parse detail {detail_url}: {e}")
        
        # Задержка
        import time
        time.sleep(1)
    
    return records


# ─── Pagination ─────────────────────────────────────────────────

def parse_all_pages(base_url, profile):
    """Обработка пагинации."""
    selectors = profile.get("selectors", {})
    method = profile.get("parsing_method", "requests")
    structure = profile.get("data_structure", "table")
    pagination_type = profile.get("pagination_type")
    max_pages = profile.get("max_pages", 5)
    
    all_records = []
    page_size = profile.get("page_size", 50)
    offset = 0
    
    for page_num in range(max_pages):
        # Формируем URL в зависимости от типа пагинации
        if pagination_type == "url_pattern":
            url = base_url.format(page=page_num + 1)
        elif pagination_type == "offset":
            sep = "&" if "?" in base_url else "?"
            url = f"{base_url}{sep}offset={offset}&limit={page_size}"
        elif pagination_type == "page":
            sep = "&" if "?" in base_url else "?"
            url = f"{base_url}{sep}page={page_num + 1}"
        else:
            url = base_url
        
        print(f"  Страница {page_num + 1}/{max_pages}: {url[:80]}...")
        
        html = fetch_page(url, method=method)
        if not html:
            break
        
        if structure == "table":
            records = parse_table_page(html, selectors, url)
        elif structure == "card":
            records = parse_card_page(html, selectors, url)
        elif structure == "spa":
            records = parse_spa_page(url, selectors)
        else:
            records = parse_table_page(html, selectors, url)
        
        if not records:
            print(f"  [END] Нет записей на странице {page_num + 1}")
            break
        
        all_records.extend(records)
        print(f"  [+] {len(records)} записей (всего: {len(all_records)})")
        
        offset += len(records)
        
        # Если записей меньше page_size — это последняя страница
        if len(records) < page_size:
            break
        
        import time
        time.sleep(1)
    
    return all_records


# ─── Save to Supabase ───────────────────────────────────────────

def save_to_supabase(records, source_name, profile_id):
    """Сохранить записи в raw_parsed_data."""
    if not SUPABASE_KEY:
        print("[ERROR] SUPABASE_SERVICE_KEY не задан")
        return
    
    payload = []
    for r in records:
        rec = {
            "name": r.get("name", ""),
            "country": r.get("country", ""),
            "phone": r.get("phone", ""),
            "email": r.get("email", ""),
            "website": r.get("website", ""),
            "description": r.get("description", ""),
            "source": source_name,
        }
        payload.append(rec)
    
    if not payload:
        return
    
    # Батчами по 100
    batch_size = 100
    saved = 0
    for i in range(0, len(payload), batch_size):
        batch = payload[i:i+batch_size]
        result = sb_upsert("raw_parsed_data", batch)
        if result:
            saved += len(batch)
    
    print(f"[SAVE] {saved}/{len(records)} записей сохранено в raw_parsed_data")
    
    # Обновляем счётчик в профиле
    sb_update("source_profiles", profile_id, {
        "success_count": saved,
        "last_verified": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
    })


# ─── Main ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Универсальный парсер каталогов")
    parser.add_argument("--list", action="store_true", help="Список профилей")
    parser.add_argument("--source", type=str, help="Имя источника (source_name)")
    parser.add_argument("--url", type=str, help="URL для поиска профиля")
    parser.add_argument("--all", action="store_true", help="Все профили")
    parser.add_argument("--details", action="store_true", help="Загрузить детали")
    parser.add_argument("--dry-run", action="store_true", help="Не сохранять в БД")
    parser.add_argument("--max-pages", type=int, help="Макс страниц")
    
    args = parser.parse_args()
    
    if args.list:
        list_profiles()
        return
    
    # Загружаем профиль
    profiles = load_profiles(source_name=args.source, url=args.url)
    if not profiles and (args.source or args.url):
        # Пробуем найти по частичному совпадению
        all_p = load_profiles()
        if args.source:
            matches = [p for p in all_p if args.source.lower() in p.get('source_name','').lower()]
            if matches:
                profiles = matches
    
    if not profiles:
        print(f"[ERROR] Профиль не найден (source={args.source}, url={args.url})")
        print("Доступные профили:")
        list_profiles()
        return
    
    if args.all:
        # Все профили
        pass
    else:
        profiles = profiles[:1]
    
    for profile in profiles:
        source_name = profile.get("source_name", "unknown")
        url = profile.get("url", "")
        profile_id = profile.get("id", "")
        
        print(f"\n{'='*60}")
        print(f"Парсинг: {source_name}")
        print(f"URL: {url}")
        print(f"Метод: {profile.get('parsing_method')} | Структура: {profile.get('data_structure')}")
        print(f"{'='*60}")
        
        if args.max_pages:
            profile["max_pages"] = args.max_pages
        
        # Парсим
        records = parse_all_pages(url, profile)
        
        if not records:
            print(f"[RESULT] Нет записей для {source_name}")
            continue
        
        # Детали
        if args.details and profile.get("needs_detail_page"):
            print(f"\n[DETAILS] Загрузка деталей...")
            base_url = "/".join(url.split("/")[:3])
            records = fetch_details(records, profile, base_url)
        
        # Сохраняем
        if not args.dry_run:
            save_to_supabase(records, source_name, profile_id)
        else:
            print(f"[DRY-RUN] {len(records)} записей (не сохранено)")
            for r in records[:5]:
                print(f"  - {r.get('name', '?')[:60]} | {r.get('country', '')}")


if __name__ == "__main__":
    main()
