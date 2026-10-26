## 2024-05-24 - Bulk DB Inserts N+1 query issue

**Learning:** `add_many()` repository methods skip individual model `flush()` and `refresh()`, significantly optimizing bulk insertion performance.
**Action:** Always check if a loop containing `.add()` calls can be refactored to `.add_many()` method for N+1 optimization.
