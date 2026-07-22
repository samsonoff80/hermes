# Dead Source Detection for Parser Scripts (27.06.2026)

When maintaining parser scripts in `layer3-parser/scripts/parsers/`, always verify sources are alive before adding them to the codebase.

## Quick Source Check

```bash
curl -s -o /dev/null -w "%{http_code}" --max-time 8 "<url>"
```

- `200` — source may work (check if it's a SPA)
- `404` — page not found, source likely dead
- `000` — DNS fail or timeout, source dead
- `403` — blocked, may need proxy

## SPA Detection

If page returns HTML but no actual content links:
- Look for `<div id="root">` or `<div id="app">` (React/Vue/Angular SPA)
- Look for "Site under construction"
- Look for only CSS/JS links, no data links

## Dead Source Patterns (CIS specific)

| Pattern | Example | Status |
|---------|---------|--------|
| Tilda SPA | madeinuzbekistan.ru | Requires Playwright |
| Under construction | bozor.tj | Dead |
| Wrong content type | inform.kg (horoscope) | Dead |
| 404 on target URL | georgiayp.com/food-industry | Dead |
| No links found | n4.biz | Dead (SPA) |

## Action on Dead Source

1. Remove the parser file (if dedicated)
2. Remove the parse function (if in shared file like parse_catalogs.py)
3. Update SOURCES_CONSENSUS.json → move to dead_sites
4. Update PROGRESS.md

## Lesson Learned

In 27.06.2026 audit: `parse_catalogs.py` had 5 sources, ALL DEAD. The file was created based on Consilium recommendations but sources were never verified with curl before adding to code.

**Rule:** ALWAYS `curl` a source before writing a parser for it.
