## YYYY-MM-DD - Optimize bulk database inserts
**Learning:** The application was experiencing N+1 query patterns during bulk insertions in repositories (e.g., `DocumentTagRepository`, `DocumentChunkRepository`). Each inserted record triggered a separate `session.refresh()` query.
**Action:** Add `add_many()` repository methods that utilize `session.add_all()` to insert models efficiently without triggering per-record queries. Update the upstream service layer to call these new methods when inserting multiple related records.
