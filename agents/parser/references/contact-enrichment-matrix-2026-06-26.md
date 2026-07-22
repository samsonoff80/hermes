# Contact Enrichment Matrix — 26.06.2026

## Methods Ranked by Effectiveness

### 1. web_search (Hermes built-in) via execute_code — ⭐ BEST
- **Hit rate:** 60-67% ✅ confirmed 28.06.2026
- **Speed:** ~20 records per 300s (execute_code timeout limit)
- **Cost:** free
- **Works for:** any company with web presence
- **Critical:** Can ONLY run inside execute_code (no standalone Python)
- **Pattern:** see `references/contact-enrichment-resumable-pattern-2026-06-28.md`
- **Query:** `"{clean_name} {country} телефон email сайт"` (Russian works better for CIS)
- **Extract from:** title + description + snippet (all 5 results combined)

### 2. Playwright site parsing
- **Hit rate:** site-dependent
- **Speed:** slow (page load + render + scroll)
- **Cost:** free
- **Working sites:** produkt.by (BY), factories.kz (KZ)
- **Blocked sites:** flagma.kz/uz (blocks headless), krb.by (DNS), osoo.kg (JS-render)
- **Pattern:**
  ```python
  page.goto(url, wait_until='networkidle', timeout=20000)
  time.sleep(2)
  for _ in range(3): page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
  companies = page.query_selector_all('div.company-card a, h2 a, h3 a')
  ```

### 3. DaData API
- **Hit rate:** 0% for non-entities, works only for legal entities (ООО/ТОО/АО/ИП)
- **Speed:** 3 rec/s
- **Cost:** free
- **Why 0%:** Most records are short category names ("Кондитерские изделия"), not legal entity names
- **Only use when:** record name contains ООО/ТОО/АО/ИП/LTD/LLC

### 4. Serper API
- **Status:** 403 Forbidden — key exhausted (26.06.2026)
- **Was:** 100 requests/day, good quality for RU/TR/EU

### 5. Cloudflare AI
- **Hit rate:** ~63% for phone/email/website
- **Limit:** ~2,740 requests before 429
- **Speed:** slow (30s+ per request)
- **Use case:** small batches <2000, not for 14K records

## Recommended Strategy

For mass enrichment (>1K records):
1. **First:** web_search for all records (60-67% get contacts)
2. **Then:** Playwright for specific sites per country (remaining with known URLs)
3. **Finally:** Accept that ~30-40% will remain without contacts (categories, not companies)

## Cron Job Pattern
```
Schedule: every 5 min × 30 repeats
Per run: 50 records via web_search
Expected: ~1500 enriched in 2.5 hours
```
