## 2024-05-15 - Array Indexing on Repository List Methods Anti-Pattern
**Learning:** Using array indexing on list methods like `list_for_job(limit=1000)[-1]` to find maximum sequence numbers loads up to 1000 records into application memory and causes N+1 query-like inefficiencies in job execution contexts.
**Action:** Instead of listing all events to determine the next sequence number, implement and use a `get_max_sequence_no` repository method leveraging O(1) SQL aggregation queries (`select(func.coalesce(func.max(Model.sequence_no), 0))`).
