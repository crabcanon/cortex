## YYYY-MM-DD - Avoid N+1 query patterns during bulk insertions
**Learning:** Calling `await session.add()` in a loop creates an N+1 query pattern because it triggers a per-record `flush()` and `refresh()`. Using `session.add_all()` alone does not solve this if wrapped in a loop that awaits each addition.
**Action:** Implement `add_many()` repository methods to build a list of models and execute a single `await session.flush()` while skipping `session.refresh()` for optimal bulk insertion performance.
