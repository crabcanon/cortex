## YYYY-MM-DD - ⚡ Bolt: Optimize bulk database inserts
**Learning:** Replacing `await repo.add()` loop with `add_many()` utilizing `session.add_all()` and a single `session.flush()` resolves N+1 query patterns during bulk insertions.
**Action:** Use `add_many()` method for bulk insert operations.
