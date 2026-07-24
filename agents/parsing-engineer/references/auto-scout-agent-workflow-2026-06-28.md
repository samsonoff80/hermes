# auto_scout + consilium_brain Agent Workflow — 28.06.2026

## Key Discovery
`auto_scout_v2.py` and `consilium_brain.py` are **NOT executable scripts** — they are instruction documents for the agent. The agent READS them, then performs the work using web_search and execute_code directly.

## auto_scout_v2.py Pattern
The script at `~/.hermes/skills/layer3-parser/scripts/auto_scout_v2.py` tells the agent:
1. Use `web_search` for each CIS country × food category
2. Collect URLs from search results
3. Verify each URL with curl (8s timeout)
4. Classify: catalog (keep) vs informational (skip) vs dead (skip)
5. INSERT valid ones into `source_profiles`

## consilium_brain.py Pattern
The script at `~/.hermes/skills/layer3-parser/scripts/consilium_brain.py` tells the agent:
1. Use `consilium_ask()` to analyze HTML pages
2. Determine if page is a business catalog worth parsing
3. Extract company data using regex patterns
4. Return structured data ready for raw_parsed_data

## How Agent Actually Executes
The agent doesn't `python3 auto_scout_v2.py` — instead it:
1. Reads the script file to understand the instructions
2. Uses `execute_code` with `hermes_tools.web_search` for searching
3. Uses `execute_code` with urllib for Supabase INSERT
4. Uses `execute_code` for HTML parsing (regex, not BeautifulSoup)

## Correct Execution Sequence
```
1. skill_view('layer3-parser') → read auto_scout_v2 instructions
2. execute_code: web_search per country × category → collect URLs
3. execute_code: curl verify each URL → filter
4. execute_code: INSERT source_profiles (NOT source_metadata column!)
5. execute_code: parse each source_profile → regex extract companies
6. execute_code: dedup by (name, country) → INSERT raw_parsed_data
7. execute_code: pipeline_v55_final.py (can run standalone)
8. execute_code: web_search enrichment (batches of 25)
```

## Supabase Schema for source_profiles (28.06.2026)
Only safe columns: `id, name, url, country, method, status, created_at`
- `method`: "requests" or "playwright"
- `status`: "active" or "dead"
- NO `source_metadata` column (causes PGRST204)

## CIS Countries for Scout (9)
Россия, Казахстан, Узбекистан, Армения, Азербайджан, Кыргызстан, Таджикистан, Туркменистан, Грузия
(Беларусь excluded per user preference)
