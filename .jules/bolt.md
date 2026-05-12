## 2024-05-12 - Sequence Aggregation Optimization

**Learning:** Array indexing on repository list methods (e.g., `list_for_job(limit=1000)[-1]`) to determine maximum sequence numbers is an anti-pattern. It loads large numbers of records into application memory just to find an aggregate, mimicking N+1 inefficiency on high-cardinality collections like job events.
**Action:** Use direct SQLAlchemy aggregation queries (`select(func.coalesce(func.max(Model.sequence_no), 0))`) in a dedicated repository method to ensure O(1) performance in both the database calculation and application memory usage.
