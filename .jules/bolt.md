## 2026-06-01 - Optimize fetching max sequence number using SQL aggregation

**Learning:** Using array indexing on list queries to fetch the max sequence number (e.g. `list_for_job(...)[-1]`) pulls many records into memory leading to performance issues and inefficient DB access. It represents an anti-pattern when we only need the maximum sequence number.

**Action:** Add direct direct SQL aggregations, such as `select(func.coalesce(func.max(Model.sequence_no), 0))` in repository methods, to calculate maximum sequence numbers avoiding the loading of the actual events data into memory to achieve an $O(1)$ efficiency in terms of fetched DB items. Always use this pattern when calculating numbers.
