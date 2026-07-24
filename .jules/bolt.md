## 2025-02-18 - [JobEvent Sequence Number Optimization]
**Learning:** Loading all items to get the max sequence number using `list_for_job(job_id, limit=1000)[-1]` is highly inefficient because it loads unnecessary records into memory causing N+1 query-like inefficiencies.
**Action:** Use direct SQLAlchemy aggregation queries (e.g., `select(func.coalesce(func.max(Model.field), 0))`) in the repository methods for $O(1)$ efficiency.
