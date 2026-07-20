# parse_catalogs.py → Supabase Schema Pitfall (28.06.2026)

## Problem
`parse_catalogs.py` save_to_supabase() initially failed with:
- `PGRST204: Could not find the 'city' column`
- `PGRST204: Could not find the 'source_url' column`  
- `PGRST204: Could not find the 'raw_data' column`

These columns don't exist in `raw_parsed_data` schema.

## Real raw_parsed_data Schema (verified 28.06.2026)
```sql
id, name, name_clean, country, phone, email, website, description, 
source, is_duplicate, duplicate_of, dedup_method, dedup_confidence, created_at
```

## Correct payload for parse_catalogs.py
```python
rec = {
    "name": r.get("name", ""),
    "country": r.get("country", ""),
    "phone": r.get("phone", ""),
    "email": r.get("email", ""),
    "website": r.get("website", ""),
    "description": r.get("description", ""),
    "source": source_name,
}
# DO NOT include: city, source_url, raw_data
# DO NOT include: id (auto-generated UUID)
```

## Also: source_profiles has no 'source_metadata' column
When inserting to source_profiles, do NOT include `source_metadata`. Only use:
```python
{
    "url", "domain", "source_name", "content_type", "parsing_method",
    "data_structure", "selectors", "has_pagination", "pagination_type",
    "max_pages", "phone_on_list", "email_on_list", "website_on_list",
    "needs_detail_page", "detail_selectors", "last_verified",
    "success_count", "fail_count", "created_at", "updated_at"
}
```

## Lesson
ALWAYS verify actual table schema via `GET /rest/v1/table?limit=1` before writing INSERT code. Don't assume column names from documentation.
