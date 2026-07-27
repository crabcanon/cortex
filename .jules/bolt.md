
## 2024-07-27 - Optimize Job Event Sequence Calculation
**Learning:** Loading lists of entities into memory (e.g., using `list_for_job(limit=1000)[-1]`) just to determine the maximum sequence number is an anti-pattern that behaves like an N+1 query memory leak.
**Action:** Always use direct SQL aggregations (e.g., `select(func.coalesce(func.max(Model.field), 0))`) in repository methods to fetch scalar maximums in O(1) time rather than loading unneeded objects into memory.
