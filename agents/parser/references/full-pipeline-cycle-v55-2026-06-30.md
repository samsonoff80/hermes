# Full Pipeline V5.5 Cycle — 30.06.2026 Run

## What Happened
Complete end-to-end run: 51,391 raw records → pipeline_v55_final.py → 20,065 clean_clients.

## Source Data
| Source | Records | Has contacts? |
|--------|---------|---------------|
| prodexpo_pdf_all (18K) | ~5% phone, ~12% email | Mostly description only |
| worldfood_moscow_205 (10K) | 0% phone, 0% email | description + country |
| prodexpo_pdf_v3 (6K) | ~5% phone | description |
| foodmarkets (4K) | 95%+ phone | Full contacts |
| Others (13K) | Varies | Varies |

## Pipeline V5.5 Results
```
Processed: 51,391 records in 21.0s (2,442 rec/s)
Rejected: 31,095 (60.5%)
Grey zone: 11,856 (23.1%)
Accepted: 20,296 (39.5%)

Top reject reasons:
- fuzzy_dedup: 20,756 (duplicate names across years)
- exact_dedup: 6,796
- high_score:45: 4,942
- high_score:65: 3,188
```

## Country Distribution (clean_clients)
| Country | Count |
|---------|-------|
| Россия | ~9,152 (merged from "Russia" + "Россия") |
| Китай | ~3,191 |
| Турция | ~918 |
| Казахстан | ~150+ |
| None | ~3,976 (— from "worldfood_moscow_2025" which uses English names) |

## Contact Coverage (clean_clients)
| Field | Count | % |
|-------|-------|---|
| phone | 3,181 | 15.7% |
| email | 1,080 | 5.3% |
| website | 1,183 | 5.8% |
| description | 17,153 | 84.5% |

## Critical Insight
**New sources (worldfood, prodexpo_pdf) have RICH descriptions but NO contacts.** The pipeline correctly deduplicates them, but contact coverage drops from 97% (foodmarkets-only) to 15%.

### Next Priority: Contact Enrichment
- 17,000+ records need phone/email/website enrichment
- web_search can find contacts but is slow (~50 rec/min)
- Consider: website column → scrape contact pages → extract phone/email
- Or: company name → web_search("company name контакты телефон email")

## Country Normalization Done
Applied mapping during clean_clients upload:
- Russia → Россия (merged 4,889 + 4,263 into ~9,152)
- China/Китай → Китай
- Türkiye/Turkey/Турция → Турция
- All CIS countries normalized to Russian names
