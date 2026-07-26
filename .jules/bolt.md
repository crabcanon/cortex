## 2024-07-26 - Optimized JobEvent sequence resolution
**Learning:** Using `list_for_job(limit=1000)[-1]` to find the maximum sequence number is an anti-pattern as it loads unnecessary records into memory causing N+1 query-like inefficiencies.
**Action:** Use direct SQLAlchemy aggregation queries (e.g., `select(func.coalesce(func.max(Model.field), 0))`) in the repository methods for $O(1)$ efficiency.
