## YYYY-MM-DD - Optimize Sequence Number Generation
**Learning:** Using `list_for_job(limit=1000)[-1]` to determine maximum sequence numbers loads unnecessary records into memory causing N+1 query-like inefficiencies. Direct SQLAlchemy aggregation queries (`select(func.coalesce(func.max(Model.field), 0))`) achieve O(1) efficiency.
**Action:** Added `get_max_sequence_no` optimized method using database-level aggregation to the `JobEventRepository` to compute the next sequence number directly, avoiding loading records into memory entirely.
