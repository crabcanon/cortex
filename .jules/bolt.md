## 2024-04-21 - [Replace Array Indexing with Database Aggregation for Max Sequences]
**Learning:** Avoid using array indexing on repository list methods (e.g., `existing_events = await uow.job_events.list_for_job(...)` followed by `existing_events[-1].sequence_no`) to determine maximum values like sequence numbers, as it loads unnecessary records into memory causing high memory usage and poor performance as tables grow.
**Action:** Use direct database aggregation queries (e.g., `select(func.max(...))`) in repository methods for $O(1)$ efficiency.
