## YYYY-MM-DD - Bulk Insert Optimization
**Learning:** Avoid N+1 query patterns during bulk insertions by utilizing `add_many()` repository methods which leverage `session.add_all()` to insert models efficiently without triggering per-record `session.refresh()` queries.
**Action:** Use `add_many()` for bulk inserting models like `DocumentTagRecord`, `DocumentChunkRecord`, `DocumentArtifactRecord`, and `ParseRunAttemptRecord` to improve parsing performance.
