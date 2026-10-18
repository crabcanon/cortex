## 2024-10-18 - Optimize bulk database inserts
**Learning:** Avoid N+1 query patterns during bulk insertions by utilizing `add_many()` repository methods instead of calling `await repo.add()` in a loop.
**Action:** Use the `add_many()` methods that build a list of models and execute a single `await session.add_all()` and `await session.flush()`, skipping the `session.refresh()` which triggers a per-record database call.
