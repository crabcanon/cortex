## YYYY-MM-DD - Avoid list fetching for max sequence number
**Learning:** Found codebase anti-pattern where `list_for_job(limit=1000)[-1]` is used to get the next sequence number for job events. This pulls up to 1000 records into memory unnecessarily and causes N+1-like inefficiency.
**Action:** Use a direct SQLAlchemy aggregation query `select(func.coalesce(func.max(Model.sequence_no), 0))` in repository methods like `get_max_sequence_no` to compute max values with O(1) efficiency.
