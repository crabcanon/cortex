## 2024-05-14 - Optimize bulk database inserts
**Learning:** Found N+1 query patterns during bulk insertions in loops in parse service (`document_tags`, `document_chunks`, `document_artifacts`) and knowledge operations (`search_hits`). Using `session.add_all` avoids per-record flushes.
**Action:** Replace `session.add()` called in a loop with `session.add_all()` wrapped in `add_many()` method on repositories to execute a single `await session.flush()` instead of triggering per-record flush and refresh.
