## 2024-05-24 - Avoid N+1 Memory Loading for Aggregations
**Learning:** Using array indexing on repository list methods (e.g., `list_for_job(limit=1000)[-1]`) to determine maximum values is an anti-pattern. It loads unnecessary records into memory causing inefficiencies similar to N+1 queries.
**Action:** Always use direct SQLAlchemy aggregation queries (e.g., `select(func.coalesce(func.max(Model.field), 0))`) in the repository methods for O(1) efficiency.
