## YYYY-MM-DD - [Title]
**Learning:** [Insight]
**Action:** [How to apply next time]

## YYYY-MM-DD - Optimize bulk database inserts
**Learning:** Found N+1 query patterns during bulk insertions in `ParsePersistenceService` (specifically for `DocumentTagRecord`, `DocumentChunkRecord`, `DocumentArtifactRecord`, and `ParseRunAttemptRecord`). Adding `add_many()` repository methods leverages `session.add_all()` to insert models efficiently without triggering per-record `session.refresh()` queries.
**Action:** Implemented `add_many()` methods in `DocumentTagRepository`, `DocumentChunkRepository`, `DocumentArtifactRepository`, and `ParseRunAttemptRepository` within `cortex_db` and updated `ParsePersistenceService` in `cortex_parse` to utilize these optimized batch insertions.
