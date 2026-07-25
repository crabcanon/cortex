## 2024-05-01 - [Avoid O(N) memory loading for Sequence Numbers]
**Learning:** Using array indexing on repository list methods (e.g., `list_for_job(limit=1000)[-1]`) to determine maximum sequence numbers loads unnecessary records into memory, causing N+1 query-like inefficiencies.
**Action:** Use direct SQLAlchemy aggregation queries (e.g., `select(func.coalesce(func.max(Model.field), 0))`) in the repository methods to achieve O(1) efficiency.
