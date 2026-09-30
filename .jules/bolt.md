## YYYY-MM-DD - ⚡ Bolt: Optimize bulk database inserts
**Learning:** Avoid N+1 query patterns during bulk insertions. `session.add_all()` in `add_many()` repository methods significantly improves efficiency by skipping per-record `session.refresh()` queries.
**Action:** When inserting multiple models where primary keys are generated upstream (like using `new_prefixed_id`), use `session.add_all()` and `session.flush()` in bulk rather than looping with `session.add()` and `session.refresh()`.
