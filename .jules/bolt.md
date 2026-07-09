## 2025-02-18 - Replacing repository array indexing with SQL aggregations
**Learning:** Using array indexing on repository list methods (e.g., `list_for_job(limit=1000)[-1]`) to determine maximum sequence numbers loads unnecessary records into memory and causes N+1 query-like inefficiencies, impacting performance.
**Action:** Use direct SQLAlchemy aggregation queries (e.g., `select(func.coalesce(func.max(Model.field), 0))`) in repository methods for $O(1)$ efficiency.
