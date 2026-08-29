## YYYY-MM-DD - Bulk Inserts For Document Parsing
**Learning:** Inserting tags, chunks, and artifacts sequentially in a loop inside `_persist_document` led to unnecessary N+1 queries. Adding and using `add_many` in the `DocumentTagRepository`, `DocumentChunkRepository`, and `DocumentArtifactRepository` leverages SQLAlchemy's `add_all` to significantly reduce database round-trips.
**Action:** Use `add_many` and `add_all` for bulk creation of related entities (like chunks or tags) instead of creating them individually inside `for` loops.
