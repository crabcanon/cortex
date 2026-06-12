## 2026-06-12 - Optimize Next Sequence Number Calculation
**Learning:** Avoid loading full lists of records into memory to determine maximum values or sequence numbers (N+1-like array indexing anti-pattern).
**Action:** Use database aggregation functions like `func.max()` via SQLAlchemy queries to calculate maximum values directly on the database engine, minimizing memory usage and transfer overhead.
