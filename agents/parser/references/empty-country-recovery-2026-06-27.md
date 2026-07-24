# Empty Country Recovery Pattern (2026-06-27)

## Problem
When cleaning `clean_clients` by country (e.g., removing non-CIS), records with empty `country` field are at risk of deletion even if they ARE from CIS countries. The country information is often present in `name` or `description` fields but wasn't parsed into the `country` column.

## Real-World Impact
- **19,463 → 7,000** records (instead of 8,143) — **1,143 records lost** due to premature deletion
- 3,008 CIS records found in empty-country pool (from `prodexpo_pdf_parsed` source)
- 2,538 successfully recovered and re-uploaded

## Root Cause
PDF exhibition catalogs (ProdExpo parser) put country information inside the company name string rather than the dedicated country field. Examples:
- `"ALTAY FOOD GIDA QAZAQSTAN,"` → Казахстан
- `"ALTUNKAYA INS. NAK. GIDA VE TIE. A.S, TÜRKIYE"` → не СНГ (Turkey)
- `"ICE-DON COMPANY"` with description `"Russia"` → Россия

## Algorithm: Recover Before Delete

### Step 1: Load all empty-country records from raw source
```python
# Two types of empty: NULL and empty string
records = sb_get('?select=id,name,description,phone,email&country=eq.')
# Also: records = sb_get('?select=id,name,description&country=is.null')
```

### Step 2: Detect country from name+description
```python
CIS_KEYWORDS = {
    "Россия": ["russia", "росси", "russian federation"],
    "Казахстан": ["kazakhstan", "казахстан", "kazakh", "qazaqstan"],
    "Узбекистан": ["uzbekistan", "узбекистан"],
    "Кыргызстан": ["kyrgyzstan", "кыргызстан", "kirghiz"],
    "Армения": ["armenia", "армения"],
    "Азербайджан": ["azerbaijan", "азербайджан"],
    "Туркменистан": ["turkmenistan", "туркменистан"],
    "Грузия": ["georgia", "грузия"],
    "Таджикистан": ["tajikistan", "таджикистан"],
}

NON_CIS = ["turkey", "türkiye", "турци", "china", "кита", "india", "индия",
           "serbia", "серби", "italy", "итали", "germany", "герман", "brazil", "бразил"]

def detect_cis(text):
    if not text: return None
    t = text.lower()
    for nc in NON_CIS:
        if nc in t: return None  # Non-CIS detected
    for country, patterns in CIS_KEYWORDS.items():
        for p in patterns:
            if p in t: return country
    return None  # Unknown
```

### Step 3: Clean name and upload CIS records
```python
for r in records:
    name = r.get("name") or ""
    desc = r.get("description") or ""
    country = detect_cis(f"{name} {desc}")
    if country:
        # Clean country suffix from name
        clean_name = re.sub(r',?\s*(RUSSIA|Russia|KAZAKHSTAN|...)\s*$', '', name, flags=re.I).strip(' ,')
        upload({
            "name_clean": clean_name,
            "country": country,
            "phone": r.get("phone"),
            "email": r.get("email"),
        })
```

### Step 4: Only then delete remaining empty/non-CIS

## Key Rules
1. **NEVER delete empty-country records without attempting recovery first**
2. **Check BOTH `country=is.null` AND `country=eq.`** — both types exist
3. **Non-CIS in name?** Use keyword blacklist to filter out Turkey, China, India etc.
4. **Recovery rate**: ~43% of empty-country records were CIS in this session (3,008/7,090)
5. **Source matters**: `prodexpo_pdf_parsed` has highest rate of empty-country CIS records

## Supabase REST API Notes
- `country=is.null` works but returns 0 results if no NULLs (some are empty strings)
- `country=eq.` catches empty strings
- Always check both conditions
- Batch upload 500 records at a time for stability

## Script Template
See `scripts/empty_country_recovery.py` (created inline in session 2026-06-27).
