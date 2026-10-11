## 2024-05-24 - Bulk DB Inserts
**Learning:** Using `await session.add()` inside a for-loop causes severe N+1 performance bottlenecks because each call flushes the transaction and triggers a `session.refresh()` query for the inserted record.
**Action:** Implement `add_many()` repository methods that build a list of models and call `session.add_all(models)` followed by a single `await session.flush()`, skipping `session.refresh()` entirely by generating primary keys at the application layer.
