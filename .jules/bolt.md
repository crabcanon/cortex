## YYYY-MM-DD - [Preventing N+1 queries during bulk insert]
**Learning:** During loop insertions of related data (like tags, chunks, artifacts) per document parse run, a per-record `.add()` executes separate `session.refresh()` calls triggering N+1 queries.
**Action:** Use `.add_many()` repository methods that wrap `session.add_all()` and omit `session.refresh()`, constructing required pre-fixed object ids before sending to DB layer to preserve performance.
