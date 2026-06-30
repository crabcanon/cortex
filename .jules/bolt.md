## 2025-02-15 - Optimize Job Events Sequence Calculation
**Learning:** Computing the next sequence number for a job by fetching all events and reading the last one (`existing_events[-1].sequence_no`) creates a performance bottleneck since it loads all events into memory (N+1 query-like inefficiencies).
**Action:** Use a direct SQLAlchemy aggregation query (`select(func.coalesce(func.max(Model.field), 0))`) in the repository to return the max value in O(1) efficiency and use that value directly.
