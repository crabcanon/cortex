## 2024-07-12 - Prevent N+1 query patterns for Job Events Sequence Numbers
**Learning:** Loading an entire list of events into memory (`list_for_job(job_id, limit=1000)`) just to determine the maximum sequence number (`existing_events[-1].sequence_no`) is an inefficient N+1 query-like pattern, particularly as job histories grow over time.
**Action:** Use direct SQLAlchemy aggregation (`select(func.coalesce(func.max(JobEventModel.sequence_no), 0))`) to calculate sequence numbers in $O(1)$ efficiency directly at the database layer.
