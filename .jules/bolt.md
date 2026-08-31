## 2026-04-26 - [Use SQL Aggregation for Sequence Numbers]
**Learning:** In the `JobEventRepository`, calculating the next sequence number by loading all existing events into memory (`existing_events = await uow.job_events.list_for_job(job_id, limit=1000)`) and reading the last one is inefficient and scales poorly as the number of events grows.
**Action:** Use SQL aggregation (`func.max()`) to calculate the maximum sequence number directly in the database, reducing memory overhead and improving performance.
