## YYYY-MM-DD - Optimize next sequence number calculation
**Learning:** Avoid using array indexing on repository list methods (e.g., `list_for_job(limit=1000)[-1]`) to determine maximum sequence numbers, as it loads unnecessary records into memory causing N+1 query-like inefficiencies.
**Action:** Use direct SQLAlchemy aggregation queries (`select(func.coalesce(func.max(Model.field), 0))`) for $O(1)$ efficiency.
