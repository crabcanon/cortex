## 2024-10-07 - Avoid N+1 queries during bulk insertions
**Learning:** During knowledge search, `SearchHitRecord` entries were being inserted one-by-one via `uow.search_hits.add()`, triggering individual `session.add()` and `session.refresh()` calls for each context item in the search response.
**Action:** Utilize bulk insertion methods (e.g., `add_many()`) for repositories which leverage `session.add_all()` to insert models efficiently without triggering per-record queries.
