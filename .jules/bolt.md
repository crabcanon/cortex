## 2024-05-24 - Repository Memory Inefficiency

**Learning:** Loading lists of database records into memory to determine the next sequence number (e.g., using `list_for_job(limit=1000)[-1]`) causes an N+1 query-like inefficiency and potential scaling issues as datasets grow.

**Action:** Always use SQL aggregation (`func.max`) within repository methods (e.g., `get_max_sequence_no`) instead of array indexing on memory-loaded list results to calculate max/next sequence numbers. This guarantees an $O(1)$ database execution and prevents memory bottlenecks.
