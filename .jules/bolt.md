## 2024-05-24 - Document chunks bulk insert efficiency
**Learning:** Found N+1 query pattern during bulk inserts (`session.add()` inside a loop) which performs poorly and triggers separate `session.refresh()` for every document chunk.
**Action:** Implement `add_many()` method in `DocumentChunkRepository` (and potentially `DocumentTagRepository`) using `session.add_all()` to insert records efficiently without triggering per-record session.refresh() queries.
