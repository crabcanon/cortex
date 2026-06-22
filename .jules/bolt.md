## 2026-06-22 - Optimize JobEventRepository Max Sequence No
**Learning:** The application had an N+1 query-like pattern for retrieving max sequence numbers for job events, pulling all events into memory just to find the max.
**Action:** Used direct SQL aggregation via `func.max` and `func.coalesce` to execute in $O(1)$ efficiency.
