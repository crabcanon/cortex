## 2024-05-18 - Bulk Insert Optimization in Repositories
**Learning:** Avoid N+1 query patterns during bulk insertions by utilizing `add_many()` repository methods (e.g., in `DocumentTagRepository`, `DocumentChunkRepository`, `DocumentArtifactRepository`, `ParseRunAttemptRepository`, `JobEventRepository`) which leverage `session.add_all()` to insert models efficiently without triggering per-record `session.refresh()` queries.
**Action:** Always implement and use `add_many()` methods when inserting multiple records of the same entity simultaneously.
