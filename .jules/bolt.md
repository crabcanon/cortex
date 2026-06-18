## 2025-06-07 - O(N) Array Access on Database Fetching Anti-pattern
**Learning:** Found a systemic anti-pattern where the maximum sequence number for Job Events was calculated by fetching all records (`list_for_job(job_id, limit=1000)`) and accessing the last element (`existing_events[-1].sequence_no`). This loaded large amounts of unnecessary data into memory.
**Action:** Always prefer direct SQL aggregations (e.g., `select(func.coalesce(func.max(Model.sequence_no), 0))`) in a dedicated repository method instead of application-level evaluation on fetched record lists.
