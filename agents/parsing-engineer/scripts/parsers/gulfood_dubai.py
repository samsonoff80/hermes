"""
Gulfood Dubai 2026 parser v2.
Full Playwright approach - navigate and extract from rendered pages.
"""
import json, re, time, os, sys
from playwright.sync_api import sync_playwright

BASE_URL = "https://exhibitors.gulfood.com"
INITIAL_URL = f"{BASE_URL}/gulfood-2026/Sectorlist/world-food"
OUTPUT_FILE = "/home/khadas/.hermes/skills/layer3-parser/data/gulfood_dubai_2026.json"

# Load existing
existing_data = []
if os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
        try:
            existing_data = json.load(f)
        except:
            existing_data = []

if len(existing_data) >= 3000:
    print(f"Already have {len(existing_data)} companies, skipping")
    sys.exit(0)

def parse_companies_from_page(html):
    """Parse company cards from HTML"""
    companies = []
    # Split by company card container
    items = re.split(r'<div class="item mb-4', html)
    for item in items[1:]:
        company = {}
        
        # Name - look for exb-title or strong/a tags
        name_match = re.search(r'class="[^"]*exb-title[^"]*"[^>]*>(.*?)</', item, re.DOTALL)
        if not name_match:
            name_match = re.search(r'<strong[^>]*>([^<]{3,})</strong>', item)
        if name_match:
            name = re.sub(r'<[^>]+>', '', name_match.group(1)).strip()
            if name and len(name) > 2:
                company['name'] = name
        
        # Country
        country_match = re.search(r'(?:country|страна)[^>]*>([^<]{2,50})</', item, re.DOTALL | re.IGNORECASE)
        if not country_match:
            # Try flag image alt or title
            flag_match = re.search(r'<img[^>]*(?:flag|country)[^>]*alt="([^"]{2,50})"', item, re.IGNORECASE)
            if flag_match:
                company['country'] = flag_match.group(1).strip()
        else:
            company['country'] = re.sub(r'<[^>]+>', '', country_match.group(1)).strip()
        
        # Stand
        stand_match = re.search(r'(?:Stand|Павильон)[^>]*>([^<]{1,20})</', item, re.IGNORECASE)
        if stand_match:
            company['stand'] = re.sub(r'<[^>]+>', '', stand_match.group(1)).strip()
        
        # Detail URL
        href_match = re.search(r'href="([^"]*ExbDetails[^"]*)"', item)
        if href_match:
            company['detail_url'] = BASE_URL + href_match.group(1)
        
        # Sector
        sector_match = re.search(r'(?:Sector|Сектор)[^>]*>([^<]{3,100})</', item, re.IGNORECASE)
        if sector_match:
            company['sector'] = re.sub(r'<[^>]+>', '', sector_match.group(1)).strip()
        
        if 'name' in company:
            companies.append(company)
    
    return companies

def main():
    print("Starting Gulfood Dubai 2026 parser v2 (full Playwright)")
    
    all_companies = existing_data.copy()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # Intercept AJAX responses
        ajax_data = []
        def handle_response(response):
            if 'ajaxPaginationData' in response.url:
                try:
                    body = response.text()
                    ajax_data.append({'url': response.url, 'body': body[:100]})
                except:
                    pass
        
        page.on('response', handle_response)
        
        print(f"Navigating to {INITIAL_URL}")
        page.goto(INITIAL_URL, wait_until="networkidle", timeout=60000)
        time.sleep(5)  # Wait for JS to load
        
        # Get initial page content
        content = page.content()
        companies = parse_companies_from_page(content)
        all_companies.extend(companies)
        print(f"Initial page: {len(companies)} companies, total: {len(all_companies)}")
        
        # Check for AJAX data
        if ajax_data:
            print(f"Intercepted {len(ajax_data)} AJAX responses")
            for ad in ajax_data[:3]:
                print(f"  URL: {ad['url'][:80]}")
                print(f"  Body preview: {ad['body'][:100]}")
        
        # Try to find and click "Load More" or pagination
        # First, let's see what buttons exist
        buttons = page.query_selector_all('button, a, [role="button"]')
        print(f"\nFound {len(buttons)} clickable elements")
        for btn in buttons[:20]:
            text = btn.inner_text().strip()[:50]
            if text:
                print(f"  - {text}")
        
        # Try scrolling to trigger lazy load
        print("\nScrolling to trigger lazy load...")
        for i in range(5):
            page.evaluate("window.scrollBy(0, 2000)")
            time.sleep(2)
            content = page.content()
            new_companies = parse_companies_from_page(content)
            if len(new_companies) > len(all_companies):
                all_companies = new_companies
                print(f"  Scroll {i+1}: {len(all_companies)} companies")
        
        # Save what we have
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_companies, f, ensure_ascii=False, indent=2)
        
        print(f"\nSaved {len(all_companies)} companies to {OUTPUT_FILE}")
        
        # Debug: save page HTML for analysis
        debug_file = "/home/khadas/.hermes/skills/layer3-parser/data/gulfood_debug.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(content[:50000])
        print(f"Debug HTML saved to {debug_file}")
        
        browser.close()

if __name__ == '__main__':
    main()
