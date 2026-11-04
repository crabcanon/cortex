
## YYYY-MM-DD - Avoid N+1 query patterns during bulk database inserts
**Learning:** Calling await session.flush() and refresh() in a loop for each inserted record creates a severe bottleneck. Using session.add_all() or add() inside a loop is practically the same, since they both defer execution until flush. The real issue is the per-record flush.
**Action:** For bulk inserts, use a dedicated add_many() repository method that builds a list of models, executes a single session.flush(), and skips the session.refresh() step altogether.
