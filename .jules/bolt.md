## 2024-05-15 - Optimize Job Events Sequence Calculation
**Learning:** Codebase anti-pattern: Avoid using array indexing on repository list methods (e.g., `list_for_job(limit=1000)[-1]`) to determine maximum sequence numbers, as it loads unnecessary records into memory causing N+1 query-like inefficiencies.
**Action:** Use direct SQLAlchemy aggregation queries (e.g., `select(func.coalesce(func.max(Model.field), 0))`) in the repository methods for $O(1)$ efficiency. Implemented `get_max_sequence_no` in `JobEventRepository` to compute the sequence without fetching all events.
