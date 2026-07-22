# Pipeline V5.5 Double-Counting Bug (26.06.2026)

## Problem
In `pipeline_v55_final.py`, the `reject_reasons` dict in `metrics.json` contains inflated counts because when a company passes the scoring phase (e.g. `high_score:45`) but is then rejected by `fuzzy_dedup`, BOTH `high_score:45` AND `fuzzy_dedup` are incremented.

## Root Cause
Lines 347-354 in pipeline_v55_final.py:
```python
if result:  # passed scoring
    if self.fuzzy.is_duplicate(name):
        result = False
        self.reject_reasons["fuzzy_dedup"] += 1  # Always added

if not result:
    self.metrics["rejected"] += 1
    self.reject_reasons[reason] += 1  # Original reason also added
```

So a company with score=45 that is a fuzzy duplicate gets counted in BOTH `high_score:45` AND `fuzzy_dedup`.

## Impact
- `rejected` count is CORRECT (each record counted once)
- `reject_reasons` values are INFLATED (double-counted)
- `rejected.csv` has correct data — use it for accurate statistics

## Fix
Track whether fuzzy_dedup was the reason, and if so, don't add the score reason:
```python
if result:
    if self.fuzzy.is_duplicate(name):
        result = False
        reason = "fuzzy_dedup"  # Override the score reason
        self.reject_reasons["fuzzy_dedup"] += 1
```

## Real Results (26.06.2026 run)
- Total: 76,091
- Rejected: 52,505 (69.0%)
- True breakdown from rejected.csv:
  - fuzzy_dedup: 26,927 (35.4%)
  - exact_dedup: 12,673 (16.6%)
  - grey_zone (20-39): 11,407 (15.0%)
  - low_score (<25): 6,705 (8.8%)
  - high_score (rejected by dedup): 7,433 (9.8%) — these are counted twice in metrics.json
