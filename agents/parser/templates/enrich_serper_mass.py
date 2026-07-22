#!/usr/bin/env python3
"""Mass enrichment of clean_clients using Serper API - continuous mode
Patched: 27.06.2026 — key working, added 200→500 batch, country inference
Usage: python3 enrich_serper_mass.py 2>&1 | tee /tmp/serper_mass.log"""
import os, json, urllib.request, re, time, sys
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)

with open(os.path.expanduser('~/.hermes/.env')) as f:
    for line in f:
        l = line.strip()
        if '=' in l and not l.startswith('#'):
            k, v = l.split('=', 1)
            os.environ[k] = v

SU = os.environ['SUPABASE_URL']
SK = os.environ['SUPABASE_SERVICE_KEY']
SERPER = os.environ.get('SERPER_API_KEY', '')

def sb_get(path):
    req = urllib.request.Request(f'{SU}/rest/v1/clean_clients{path}',
        headers={'apikey': SK, 'Authorization': f'Bearer {SK}'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

def sb_post(batch):
    payload = json.dumps(batch).encode()
    req = urllib.request.Request(f'{SU}/rest/v1/clean_clients',
        data=payload, method='POST',
        headers={'apikey': SK, 'Authorization': f'Bearer {SK}',
                 'Content-Type': 'application/json', 'Prefer': 'return=minimal'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status

def sb_patch(rid, data):
    req = urllib.request.Request(f'{SU}/rest/v1/clean_clients?id=eq.{rid}',
        data=json.dumps(data).encode(), method='PATCH',
        headers={'apikey': SK, 'Authorization': f'Bearer {SK}',
                 'Content-Type': 'application/json', 'Prefer': 'return=minimal'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status

def serper_search(query, num=5):
    payload = json.dumps({"q": query, "num": num, "gl": "ru", "hl": "ru"}).encode()
    req = urllib.request.Request("https://google.serper.dev/search",
        data=payload, headers={'X-API-KEY': SERPER, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())

def is_real_phone(phone):
    if not phone: return False
    d = re.sub(r'\D', '', phone)
    if len(d) == 12 and not phone.startswith('+'): return False  # BIN/IIN
    return 10 <= len(d) <= 13

def is_real_website(url):
    if not url: return False
    skip = ['youtube.com','facebook.com','instagram.com','2gis.','yandex.ru','google.',
            'icatalog.expocentr.ru','ba.prg.kz','docrobot.kz','biznesinfo.kz','statsnet.co',
            'kazakhstanyp.com','orginfo.kz','wikipedia','wildberries','ozon.ru']
    return not any(s in url for s in skip)

BATCH = 500
offset = 0
total_enriched = 0
total_phones = 0
total_emails = 0
total_websites = 0
total_processed = 0
errors = 0

while True:
    # Get records without ANY contacts
    records = sb_get(f'?select=id,name_clean,country&phone=is.null&email=is.null&website=is.null&limit={BATCH}&offset={offset}')
    if not records:
        print(f"\nNo more records! Total processed={total_processed} enriched={total_enriched}", flush=True)
        break
    
    print(f"\n--- Batch offset={offset}, got {len(records)} records ---", flush=True)
    
    for i, r in enumerate(records):
        name = r.get('name_clean', '')
        country = r.get('country', '') or ''
        if not name or len(name) < 4:
            continue
        
        # Clean name from artifacts
        clean = re.sub(r'[,.]?\s*(ПАВ|ЗАЛ|СТЕНД|PAV|HALL|STAND|ОБОРУДОВАНИЕ|БАКАЛЕЯ|МОЛОЧНЫЕ ПРОДУКТЫ|КОНДИТЕРСКИЕ И ХЛЕБОБУЛОЧНЫЕ ИЗДЕЛИЯ|ЖИРЫ И МАСЛА|ПОЛУФАБРИКАТЫ|ДРУГОЕ|ТОРГОВЫЕ, ОТРАСЛЕВЫЕ АССОЦИАЦИИ).*', '', name, flags=re.I).strip()
        for suffix in ['ТОО', 'ООО', 'АО', 'ИП', 'СП', 'LTD', 'LLC', 'JSC', 'INC']:
            clean = clean.replace(suffix, '').strip(' ,')
        
        if len(clean) < 3:
            continue
        
        query = f"{clean} {country} контакты телефон сайт".strip()
        
        try:
            result = serper_search(query, 5)
        except Exception as e:
            if '429' in str(e):
                print("  Rate limited! Sleeping 60s...", flush=True)
                time.sleep(60)
                continue
            errors += 1
            if errors > 50:
                print("  Too many errors, stopping.", flush=True)
                break
            continue
        
        organic = result.get('organic', [])
        kg = result.get('knowledgeGraph', {})
        
        found = {}
        name_words = [w for w in clean.lower().split() if len(w) > 2]
        
        if kg and kg.get('title', '').lower() in clean.lower():
            if kg.get('website'):
                found['website'] = kg['website']
            if kg.get('phoneNumber'):
                found['phone'] = kg['phoneNumber']
        
        for item in organic:
            title = item.get('title', '')
            url = item.get('link', '')
            snippet = item.get('snippet', '')
            
            if name_words and not any(w in title.lower() for w in name_words):
                continue
            
            phones = re.findall(r'\+?\d[\d\s\(\)-]{7,}', snippet)
            for p in phones:
                if is_real_phone(p) and 'phone' not in found:
                    found['phone'] = p.strip()
                    break
            
            emails = re.findall(r'[\w.+-]+@[\w.-]+\.\w+', snippet)
            if emails and 'email' not in found:
                found['email'] = emails[0]
            
            if is_real_website(url) and 'website' not in found:
                found['website'] = url
            
            if 'phone' in found and 'email' in found:
                break
        
        if found:
            try:
                sb_patch(r['id'], found)
                total_enriched += 1
                if 'phone' in found: total_phones += 1
                if 'email' in found: total_emails += 1
                if 'website' in found: total_websites += 1
            except:
                pass
        
        total_processed += 1
        
        if total_processed % 50 == 0:
            print(f"  [{total_processed}] enriched={total_enriched} phones={total_phones} emails={total_emails} sites={total_websites} errors={errors}", flush=True)
        
        time.sleep(0.3)  # Rate limit
    
    offset += BATCH

print(f"\n=== FINAL ===", flush=True)
print(f"  Processed: {total_processed}", flush=True)
print(f"  Enriched: {total_enriched} ({100*total_enriched/max(total_processed,1):.0f}%)", flush=True)
print(f"  Phones: {total_phones}", flush=True)
print(f"  Emails: {total_emails}", flush=True)
print(f"  Websites: {total_websites}", flush=True)
