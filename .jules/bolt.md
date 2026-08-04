## YYYY-MM-DD - [Eliminate N+1 array-indexing on list_for_job with SQL aggregation max_sequence_no]
**Learning:** Using `list_for_job(limit=1000)[-1]` to fetch max sequences from DB repositories creates memory and CPU inefficiencies by eagerly pulling large datasets when all we want is a sequence number.
**Action:** Implement and use a `$O(1)$` equivalent SQL aggregation (`select(func.coalesce(func.max(Model.field), 0))`) in the repository methods.
