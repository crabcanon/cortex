## 2024-05-18 - Optimize sequence number calculation in database operations
**Learning:** Avoid using array indexing on repository list methods (e.g., `list_for_job(limit=1000)[-1]`) to determine maximum sequence numbers, as it loads unnecessary records into memory causing latency and high memory usage.
**Action:** Use direct SQLAlchemy aggregation queries (e.g., `select(func.max(...))`) in the repository methods for $O(1)$ database execution and zero unnecessary memory overhead.
