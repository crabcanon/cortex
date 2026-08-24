## YYYY-MM-DD - Avoid Array Indexing for Database Aggregations
**Learning:** Using array indexing on list methods (like `list_for_job(...)[-1]`) loads unnecessary records into memory causing N+1 query-like inefficiencies in repository usage.
**Action:** Implement and use direct SQL aggregation queries, such as `select(func.coalesce(func.max(Model.field), 0))`, to calculate maximum sequence numbers for better memory efficiency.
