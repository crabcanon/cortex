## 2025-03-05 - Avoid array indexing for sequence generation
**Learning:** Loading lists of database records into memory (e.g., `list_for_job(limit=1000)[-1]`) to determine the next sequence number is an anti-pattern. It creates unnecessary network traffic and memory bloat, acting similarly to an N+1 query issue as job events grow.
**Action:** Use direct database aggregation queries instead (`select(func.coalesce(func.max(Model.field), 0))`) in the repository methods for $O(1)$ efficiency.
