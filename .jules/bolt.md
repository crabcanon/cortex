## 2024-05-13 - Avoid Array Indexing for Database Aggregations
**Learning:** Using list methods (like `[-1]`) on repository `list` operations to calculate max sequence numbers causes N+1 like query inefficiencies by pulling 1000 records into memory.
**Action:** Used `func.coalesce(func.max(field), 0)` in an aggregation query, making sequence calculation O(1) in the repository layer.
