## YYYY-MM-DD - Bulk Insert Optimization
**Learning:** Database bulk inserts with per-record flush() and refresh() create a significant N+1 query bottleneck.
**Action:** Instead of wrapping `add()` calls in a loop, implement `add_many()` repository methods that batch models into a single `session.add_all()` and `session.flush()`, skipping the expensive `session.refresh()` step.
