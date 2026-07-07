
## 2026-07-07 - Avoiding N+1 sequence fetching with repository aggregation
**Learning:** Using array indexing on repository list methods (e.g., `list_for_job(limit=1000)[-1]`) to determine maximum sequence numbers is an anti-pattern that loads unnecessary records into memory and causes N+1 query-like inefficiencies.
**Action:** Use direct SQLAlchemy aggregation queries (e.g., `select(func.coalesce(func.max(Model.field), 0))`) in dedicated repository methods like `get_max_sequence_no` to execute aggregations purely at the database level for $O(1)$ efficiency.
