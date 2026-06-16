## 2024-05-24 - Avoid N+1 Query Inefficiencies for Sequence Numbers
**Learning:** Loading large lists of records into memory just to calculate a maximum value (e.g., `list_for_job(limit=1000)[-1]`) causes severe memory bloat and N+1 query-like performance degradation in Python backends.
**Action:** Use direct SQLAlchemy aggregation queries (e.g., `select(func.coalesce(func.max(Model.field), 0))`) in repository methods (like `get_max_sequence_no`) to perform these calculations with $O(1)$ database efficiency.
