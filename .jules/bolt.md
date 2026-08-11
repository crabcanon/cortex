## YYYY-MM-DD - Optimize job event sequence number calculation
**Learning:** Avoid loading large lists of records into memory just to determine the next sequence number (e.g. `list_for_job(limit=1000)[-1]`). This causes unnecessary object instantiation and database overhead.
**Action:** Use direct SQLAlchemy aggregation queries (e.g. `select(func.coalesce(func.max(Model.field), 0))`) in the repository for $O(1)$ efficiency.
