
## 2025-02-18 - Avoid loading large event lists to find max sequence number
**Learning:** Using `list_for_job(..., limit=1000)[-1]` to determine the maximum sequence number is an O(N) anti-pattern that creates an N+1 query-like inefficiency by loading unnecessary records into memory.
**Action:** Use a dedicated direct SQL aggregation query (e.g., `select(func.coalesce(func.max(Model.field), 0))`) in a repository method for O(1) efficiency.
