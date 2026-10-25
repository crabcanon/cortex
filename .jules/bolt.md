## 2024-10-25 - Avoid N+1 query patterns during bulk insertions
**Learning:** Calling `await repo.add()` inside a loop triggers per-record `flush()` and `refresh()`, causing performance bottlenecks. Since `session.add_all()` is just a wrapper around `session.add()` and defers SQL execution, the true fix is to collect models and execute a single `flush()` while skipping `refresh()`.
**Action:** Replace looped `add()` calls with `add_many()` methods that build a list of models and perform a single `flush()`.
