## YYYY-MM-DD - [Optimize sequence_no fetching]
**Learning:** Loading all job events into memory to determine the next sequence number by taking existing_events[-1] when list_for_job fetches up to 1000 items is highly inefficient. The `JobEventRepository` should provide an optimized `get_max_sequence_no(job_id)` method for calculating next sequence numbers using SQL aggregation (e.g. `func.max`).
**Action:** Use SQL `func.max` in repository methods when we only need the maximum sequence number instead of loading all events into memory.
