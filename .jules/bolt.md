## 2024-06-25 - JobEvent Sequence Calculation Memory Overhead
**Learning:** Avoid using array indexing on repository list methods (e.g., `list_for_job(limit=1000)[-1]`) to determine maximum sequence numbers. It loads unnecessary records into memory and mimics N+1 query inefficiencies.
**Action:** Use direct SQLAlchemy aggregation queries (e.g., `select(func.coalesce(func.max(Model.field), 0))`) in dedicated repository methods like `get_max_sequence_no` to solve this in O(1) efficiency.
