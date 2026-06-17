## 2025-06-09 - Avoid O(N) array allocation for MAX sequences
**Learning:** Found an anti-pattern in the codebase where retrieving the max sequence number loaded the entire event history of a job via `list_for_job(...)[-1]` which loads 1000 records into memory when calculating next sequence numbers for event streams. This effectively caused O(N) memory and time growth.
**Action:** Use database-side MAX() aggregation `select(func.coalesce(func.max(Model.field), 0))` instead. I updated the `JobEventRepository` to include `get_max_sequence_no` and refactored the jobs logic to use it.
