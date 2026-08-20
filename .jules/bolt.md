## YYYY-MM-DD - [Database Aggregation for Sequence Numbers]
**Learning:** Using `list_for_job(limit=1000)[-1]` to find the maximum sequence number is highly inefficient (O(N) data loading).
**Action:** Used `select(func.coalesce(func.max(...), 0))` in `get_max_sequence_no` for O(1) performance instead of fetching the whole list into memory.
