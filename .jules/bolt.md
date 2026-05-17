## 2026-04-24 - Database Aggregation for Sequence Numbers
**Learning:** Avoid using array indexing on repository list methods (e.g., `list_for_job(limit=1000)[-1]`) to determine maximum sequence numbers, as it loads up to 1000 unnecessary records into memory and causes N+1 query-like inefficiencies in job processing workflows.
**Action:** Use direct SQLAlchemy aggregation queries (e.g., `select(func.coalesce(func.max(Model.field), 0))`) with `.scalar_one()` in the repository methods for O(1) time and space efficiency instead of loading events.
