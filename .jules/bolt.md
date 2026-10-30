## YYYY-MM-DD - Optimize bulk database inserts
**Learning:** Avoid N+1 query patterns during bulk insertions. Using `await repo.add()` in a loop triggers per-record `flush()` and `refresh()`, causing significant overhead.
**Action:** Use `add_many()` repository methods, which execute a single `await session.flush()` and skip `session.refresh()`, significantly improving bulk insertion performance.
