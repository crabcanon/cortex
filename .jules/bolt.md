## YYYY-MM-DD - [Optimize Sequence Number Calculations]
**Learning:** Loading large lists of records into memory just to determine the maximum sequence number (e.g., `list_for_job(limit=1000)[-1]`) causes N+1 query-like inefficiencies and high memory usage.
**Action:** Use direct SQLAlchemy aggregation queries (e.g., `select(func.coalesce(func.max(Model.field), 0))`) to determine maximum values in O(1) time.
