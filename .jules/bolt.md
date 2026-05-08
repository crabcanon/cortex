## 2025-05-18 - Replacing inefficient list [-1] max with SQL max

**Learning:** There was an anti-pattern in the codebase where retrieving the max sequence number of an entity was done via array indexing `list_for_job(...) [-1]` which loads all events into memory, creating an N+1 query-like inefficiency.
**Action:** Replace `list_for_job(limit=1000)[-1]` with `select(func.max(Model.field))` in repositories to aggregate via SQL, making it an $O(1)$ efficiency.
