## YYYY-MM-DD - Optimize Job Event Sequence Number Calculation
**Learning:** Loading large lists of records into memory just to find the max sequence number (e.g. `await uow.job_events.list_for_job(job_id, limit=1000)`) creates significant overhead and N+1 query patterns as the number of events grows.
**Action:** Use SQL aggregation (`func.max()`) in the repository to calculate max values directly in the database without instantiating SQLAlchemy models.
