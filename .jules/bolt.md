## 2024-05-18 - Optimize Maximum Sequence Number Query

**Learning:**
Calculating the maximum sequence number for job events by fetching all records (`uow.job_events.list_for_job(job_id, limit=1000)`) and accessing the last element is inefficient ($O(n)$ memory and processing) and can lead to performance bottlenecks, especially when the number of events grows. SQLAlchemy's aggregation capabilities (`func.max`) should be used directly in the database layer for an $O(1)$ database query.

**Action:**
Added a `get_max_sequence_no(job_id)` method to `JobEventRepository` to compute the maximum sequence number via SQL `coalesce(max(sequence_no), 0)`. Refactored existing occurrences where `list_for_job` was used strictly to determine the next sequence number (in parse, synthesis, evaluation, knowledge jobs, and API job services) to use this more performant query.
