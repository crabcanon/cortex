## 2024-06-14 - Replace list_for_job with get_max_sequence_no
**Learning:** Codebase anti-pattern: Using array indexing on repository list methods (e.g., `list_for_job(limit=1000)[-1]`) to determine maximum sequence numbers loads unnecessary records into memory causing N+1 query-like inefficiencies.
**Action:** Use direct SQLAlchemy aggregation queries (e.g., `select(func.coalesce(func.max(Model.field), 0))`) in the repository methods for O(1) efficiency.
