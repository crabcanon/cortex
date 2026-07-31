## YYYY-MM-DD - O(1) Job Sequence Number Retrieval
**Learning:** Using `list_for_job(..., limit=1000)[-1]` to fetch the last sequence number is an N+1 query-like inefficiency as it unnecessarily loads all records into memory.
**Action:** Instead, we should use SQL aggregation functions, like `select(func.coalesce(func.max(Model.field), 0))`, directly in the repository via a `get_max_sequence_no` method for O(1) efficiency.
