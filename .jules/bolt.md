## 2024-05-18 - Avoid loading large lists for sequence number calculation
**Learning:** Using array indexing on repository list methods (e.g., `list_for_job(limit=1000)[-1]`) to determine maximum sequence numbers loads unnecessary records into memory, causing inefficiencies.
**Action:** Use direct SQLAlchemy aggregation queries (e.g., `select(func.coalesce(func.max(Model.field), 0))`) in the repository methods for O(1) efficiency. Added `get_max_sequence_no` to `JobEventRepository` to compute this at the database level.
