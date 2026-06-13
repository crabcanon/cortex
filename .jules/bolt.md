## 2024-06-13 - Optimize Sequence Number Calculation
**Learning:** Loading lists of records (e.g., using `list_for_job`) into memory just to determine the maximum sequence number (via array indexing like `[-1]`) causes N+1 query-like inefficiencies and excessive memory usage, particularly when handling long-running jobs that generate many events.
**Action:** Always use database-level aggregations (like `func.coalesce(func.max(Model.sequence_no), 0)`) in repositories for $O(1)$ efficiency when calculating incremental sequences or retrieving maximums.
