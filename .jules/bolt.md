## YYYY-MM-DD - Avoid N+1 queries by using add_many for bulk inserts
**Learning:** Utilizing bulk insertion methods like `session.add_all()` instead of loops with individual `session.add()` and `session.refresh()` significantly improves performance by avoiding N+1 query patterns during bulk inserts.
**Action:** Always implement and use `add_many()` repository methods for bulk inserting multiple records in a single database transaction.
