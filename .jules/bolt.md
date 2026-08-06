## YYYY-MM-DD - [Optimize sequence number calculation for Job Events]
**Learning:** Fetching an entire list of events (up to 1000 items) just to determine the next sequence number by indexing the last element (`existing_events[-1].sequence_no + 1`) is highly inefficient and creates an N+1 query-like bottleneck in memory.
**Action:** Use a direct SQLAlchemy aggregation query (`select(func.coalesce(func.max(Model.field), 0))`) to calculate the max sequence number at the database level for $O(1)$ memory footprint.
