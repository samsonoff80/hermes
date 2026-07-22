"""Разведчик источников — проверка доступности и оценка качества"""
import os, json, asyncio, aiohttp, re, argparse, time
from urllib.parse import urlparse
from collections import Counter

SOURCES_INPUT = "data/SOURCES_CONSENSUS.json"
OUTPUT_FINAL = "data/sources_final.json"
PROXY_URL = "https://proton-proxy.onrender.com/proxy"
TIMEOUT = 8
PROXY_TIMEOUT = 30

def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    netloc = parsed.netloc.replace("www.", "")
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{netloc}{path}"

async def warmup_proxy(session):
    print("🔥 Прогрев Proton Proxy...")
    try:
        async with session.get(f"{PROXY_URL}?url=https://example.com",
                               timeout=aiohttp.ClientTimeout(total=PROXY_TIMEOUT)) as resp:
            print(f"   Статус: {resp.status}")
    except:
        print("   ⚠️ Прокси не ответил, продолжаем")

async def check_url(session, url, sem=None):
    if sem:
        async with sem:
            return await _check(session, url)
    return await _check(session, url)

async def _check(session, url):
    headers = {"User-Agent": "Mozilla/5.0 HermesAgent/0.15"}
    result = {"status": "❌ broken", "used_proxy": False, "is_spa": False}
    
    try:
        async with session.get(url, timeout=TIMEOUT, headers=headers, allow_redirects=True) as resp:
            if resp.status == 200:
                html = await resp.text()
                body_text = re.sub(r'<[^>]+>', '', html).strip()
                result["status"] = "✅ checked"
                if len(body_text) < 100 and 'root' in html:
                    result["is_spa"] = True
                return result
    except:
        pass
    
    try:
        async with session.get(f"{PROXY_URL}?url={url}", timeout=PROXY_TIMEOUT, headers=headers) as resp:
            if resp.status == 200:
                html = await resp.text()
                body_text = re.sub(r'<[^>]+>', '', html).strip()
                result["status"] = "✅ needs_proxy"
                result["used_proxy"] = True
                if len(body_text) < 100 and 'root' in html:
                    result["is_spa"] = True
                return result
    except:
        pass
    
    return result

def estimate_quality(name, url, src_type):
    quality, relevance = "C", 5
    
    if any(k in url for k in ['egrul', 'nalog', 'ondiris', 'openinfo', 'orginfo', 'itsoft']):
        quality = "A"
    elif any(k in url for k in ['productcenter', 'fabricators', 'candy-factory', 'wiki-prom']):
        quality = "A"
    elif any(k in url for k in ['expocentr', 'prod-expo', 'gulfood', 'worldfood']):
        quality = "B"
    elif any(k in url for k in ['flagma', 'sprav', 'yellowpages', 'yp.', 'b2bmap']):
        quality = "B"
    
    if any(k in url for k in ['candy', 'bakery', 'dairy', 'milk', 'nuts', 'snack', 'confection', 'food', 'agro', 'prod']):
        relevance = 10
    elif any(k in url for k in ['expocentr', 'worldfood', 'gulfood']):
        relevance = 8
    elif any(k in url for k in ['flagma', 'sprav', 'yellowpages']):
        relevance = 5
    elif any(k in url for k in ['egrul', 'nalog', 'ondiris']):
        relevance = 2
    
    if any(k in url for k in ['expocentr', 'gulfood', 'worldfood-istanbul']):
        listing, details = "playwright", "playwright"
    elif any(k in url for k in ['api', 'itsoft', 'opensanctions']):
        listing, details = "api", "api"
    elif 'pdf' in url.lower():
        listing, details = "pdf", "none"
    else:
        listing, details = "requests", "requests"
    
    anti_bot = "none"
    if any(k in url for k in ['osoo.kg', 'andoz.tj']):
        anti_bot = "rate_limit"
    elif any(k in url for k in ['stat.gov.kz']):
        anti_bot = "login_required"
    elif any(k in url for k in ['gulfood', 'worldfood', 'expocentr']):
        anti_bot = "cloudflare"
    
    fields = ["name", "country", "products", "activity", "description"]
    if quality in ["A", "B"]:
        fields.extend(["website", "phone"])
    if any(k in url for k in ['egrul', 'nalog', 'ondiris']):
        fields.extend(["inn", "ogrn", "bin", "address", "okved"])
    
    return {
        "source_quality": quality,
        "food_relevance": relevance,
        "listing_method": listing,
        "details_method": details,
        "anti_bot": anti_bot,
        "company_pages": src_type != "register_bulk",
        "batch_ready": anti_bot == "none",
        "email_source": ["catalog"] if quality == "A" else ["company_website"],
        "fields": list(set(fields))
    }

def dedup_sources(sources):
    seen = {}
    unique = []
    for src in sources:
        url = normalize_url(src.get("url", ""))
        if not url:
            continue
        if url in seen:
            existing = unique[seen[url]]
            existing["consensus_count"] = existing.get("consensus_count", 1) + 1
        else:
            seen[url] = len(unique)
            src["consensus_count"] = 1
            unique.append(src)
    return unique

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parallel", type=int, default=1)
    parser.add_argument("--log-raw", action="store_true")
    args = parser.parse_args()
    
    sem = asyncio.Semaphore(args.parallel) if args.parallel > 1 else None
    if args.log_raw:
        os.makedirs("data/checks_raw", exist_ok=True)
    
    with open(SOURCES_INPUT, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    all_sources = []
    for category in ["cross_exhibitions", "cross_catalogs", "cross_registers", "cross_associations"]:
        for src in data.get(category, []):
            src["_category"] = category
            all_sources.append(src)
    
    all_sources = dedup_sources(all_sources)
    print(f"📊 Источников: {len(all_sources)} (после дедупликации)")
    
    result = {
        "groups": {g: [] for g in ["Кондитерские изделия", "Молочные продукты", "Хлебобулочные изделия", "Заморозка", "Орехи и сухофрукты", "Здоровое питание", "Снеки", "Ингредиенты"]},
        "total": len(all_sources),
        "checked": 0, "broken": 0, "needs_proxy": 0, "spa": 0
    }
    
    async with aiohttp.ClientSession() as session:
        await warmup_proxy(session)
        
        tasks = [check_url(session, src.get("url", ""), sem) for src in all_sources]
        checks = await asyncio.gather(*tasks)
        
        for src, check in zip(all_sources, checks):
            name = src.get("name", "?")
            url = src.get("url", "")
            country = src.get("country", "")
            
            status = check["status"]
            if "checked" in status and "proxy" not in status:
                result["checked"] += 1
            elif "proxy" in status:
                result["needs_proxy"] += 1
            else:
                result["broken"] += 1
            
            if check["is_spa"]:
                result["spa"] += 1
            
            quality = estimate_quality(name, url, src.get("_category", ""))
            quality["listing_method"] = "playwright" if check["is_spa"] else quality["listing_method"]
            
            entry = {
                "name": name, "url": url, "country": country,
                "status": status, "is_spa": check["is_spa"],
                "consensus_count": src.get("consensus_count", 1),
                **quality
            }
            
            for group in result["groups"]:
                result["groups"][group].append(entry.copy())
    
    for g in result["groups"]:
        result["groups"][g].sort(key=lambda x: ("checked" not in x["status"], -x["food_relevance"]))
    
    with open(OUTPUT_FINAL, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ sources_final.json")
    print(f"   ✅ checked: {result['checked']}")
    print(f"   🔄 needs_proxy: {result['needs_proxy']}")
    print(f"   ❌ broken: {result['broken']}")
    print(f"   ⚡ SPA: {result['spa']}")

if __name__ == "__main__":
    asyncio.run(main())
