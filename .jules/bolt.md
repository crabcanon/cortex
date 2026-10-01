## YYYY-MM-DD - [Optimize bulk database inserts]
**Learning:** [Avoid N+1 query patterns during bulk insertions by utilizing `add_many()` repository methods (e.g., in `DocumentTagRepository`, `DocumentChunkRepository`, `DocumentArtifactRepository`, `ParseRunAttemptRepository`) which leverage `session.add_all()` to insert models efficiently without triggering per-record `session.refresh()` queries.]
**Action:** [Use `session.add_all()` without `session.refresh()` for high-volume insert routines.]
