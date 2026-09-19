## 2025-01-20 - [Avoid N+1 query patterns by utilizing add_many repository methods]
**Learning:** Adding multiple models in a loop causes individual inserts.
**Action:** Use `add_many()` repository methods (e.g., in `DocumentTagRepository`, `DocumentChunkRepository`, `DocumentArtifactRepository`, `ParseRunAttemptRepository`) which leverage `session.add_all()` to insert models efficiently without triggering per-record `session.refresh()` queries.
