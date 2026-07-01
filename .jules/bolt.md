## 2024-05-15 - [Database N+1 Anti-Pattern in List Pagination]
**Learning:** Calling `list_for_job(...)[-1]` to determine the maximum sequence number is an N+1 query-like inefficiency in Python, loading up to `limit` (e.g. 1000) rows into memory when only the maximum value is required. This drastically reduces performance and uses unnecessary memory.
**Action:** Always use SQLAlchemy aggregation queries (e.g. `select(func.coalesce(func.max(Model.field), 0))`) in the repository to evaluate max/min/counts at the database level for $O(1)$ efficiency.
