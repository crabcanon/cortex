## 2024-06-25 - Avoid array indexing for max sequence calculation
**Learning:** Loading an entire list of records into memory just to determine the next sequence number by indexing the last element (e.g., `list_for_job(limit=1000)[-1]`) introduces N+1 query-like inefficiencies, especially when event logs scale up per job.
**Action:** Use direct SQLAlchemy aggregation queries (e.g. `select(func.coalesce(func.max(Model.sequence_no), 0))`) to compute next sequence numbers directly on the database engine. This performs with $O(1)$ database efficiency.
