
## 2024-05-18 - Optimize job event sequence number calculation
**Learning:** Avoid using array indexing on repository list methods (like `list_for_job(limit=1000)[-1]`) to determine maximum sequence numbers or counts. Loading large numbers of records into memory just to determine a scalar value causes N+1 query-like inefficiencies and higher memory usage.
**Action:** Use direct SQLAlchemy aggregation queries (e.g., `select(func.coalesce(func.max(Model.field), 0))`) in the repository methods for $O(1)$ database-side efficiency.
