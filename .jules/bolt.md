## 2024-11-02 - Optimize bulk database inserts
**Learning:** Found N+1 query patterns during bulk insertions in loops in `cortex_parse` and `cortex_knowledge`. Replaced `await uow.*.add(record)` in loops with batched `await uow.*.add_many(records)` reducing database flushes and round trips.
**Action:** Always prefer `add_many()` repository methods over repeated calls to `add()` inside loops for batch processing.
