## YYYY-MM-DD - [Optimize Next Sequence Calculation for Job Events]
**Learning:** Found a memory leak/N+1-like anti-pattern where `list_for_job(limit=1000)[-1]` is used to get the next sequence number by loading up to 1000 event records into memory just to check the last one.
**Action:** Replace inefficient list loading with direct O(1) SQLAlchemy aggregations like `select(func.coalesce(func.max(Model.field), 0))` in repository methods to calculate max sequence numbers.
