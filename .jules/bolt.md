
## 2024-05-18 - Avoid loading full record lists for simple max sequence aggregations
**Learning:** We were loading lists of job events up to 1000 items into memory in Python using `list_for_job(job_id, limit=1000)` just to read the sequence number of the last item (`events[-1].sequence_no`). This creates unnecessary latency, query overload, and N+1 query-like inefficiencies in the DB layer when all we need is a maximum sequence number.
**Action:** Use direct SQLAlchemy aggregation queries (e.g., `select(func.coalesce(func.max(Model.field), 0))`) in the repository layer to calculate maximum sequence numbers efficiently in O(1) space instead of loading lists of rows into memory.
