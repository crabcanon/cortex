## 2024-09-13 - Optimize next sequence calculation in JobEventRepository
**Learning:** Loading lists of entities in memory (e.g., via `list_for_job`) to calculate simple aggregations like the next sequence number creates an O(N) memory bottleneck and unnecessary data transfer, essentially behaving like an N+1 query issue for sequence generation.
**Action:** Always use SQL aggregation functions (like `func.max`) via dedicated repository methods (e.g., `get_max_sequence_no`) instead of fetching raw rows when calculating sequence numbers or next IDs in the application tier.
