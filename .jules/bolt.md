## 2024-08-02 - [Avoid In-Memory Max Value Calculation]
**Learning:** Codebase pattern fetched large lists (up to 1000 records) from the database into application memory just to calculate a max sequence number using list indexing.
**Action:** Apply O(1) SQL aggregation queries (e.g., `func.coalesce(func.max(Model.field), 0)`) inside repositories to avoid N+1 query-like inefficiencies.
