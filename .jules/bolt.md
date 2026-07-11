## 2024-05-24 - Database Aggregation over Memory Indexing for Sequences
**Learning:** Using `list_for_job` to load up to 1000 events into memory and taking the last element index (`existing_events[-1].sequence_no + 1`) to determine the max sequence number is an extremely inefficient anti-pattern that acts like an N+1 query. This degrades performance as logs grow.
**Action:** Use direct SQLAlchemy database aggregation (`select(func.coalesce(func.max(Model.sequence_no), 0))`) to return the maximum value in $O(1)$ efficiency without fetching unwanted row payloads into application memory.
