## 2023-10-24 - Replace array loading with SQL aggregation to prevent N+1 query-like inefficiencies
**Learning:** In repository patterns, fetching entire collections (e.g. `list_for_job(limit=1000)`) just to access a max or tail value is highly inefficient because it loads unnecessary records into memory causing N+1 query-like inefficiencies.
**Action:** Use direct SQL aggregation queries (e.g. `select(func.coalesce(func.max(Model.field), 0))`) in the repository methods for O(1) efficiency and significantly better performance.
