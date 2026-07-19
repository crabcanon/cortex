## 2024-10-24 - Efficient Next Sequence Calculation for Job Events
**Learning:** The codebase previously fetched all `JobEvent` rows into memory (`list_for_job(limit=1000)[-1]`) just to determine the latest `sequence_no` when inserting a new event. This acts like an N+1 inefficiency during bulk event insertions or long-running jobs.
**Action:** Use an optimized SQL aggregation method `get_max_sequence_no` (e.g. using `select(func.coalesce(func.max(Model.sequence_no), 0))`) in the repository and query for only the scalar max instead of loading list instances.
