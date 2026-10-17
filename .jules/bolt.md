
## 2024-05-18 - Bulk insertions via add_many() method
**Learning:** Adding multiple records individually in a loop (`await uow.repository.add(record)`) triggers per-record `flush()` and `refresh()` calls which causes an N+1 query problem, slowing down bulk insertions significantly (e.g. inserting hundreds of document chunks).
**Action:** Created an `add_many(self, records)` repository method that builds a list of SQLAlchemy models and uses `session.add_all()`, followed by a single `await session.flush()`, skipping the `refresh()` to optimize database interaction during bulk operations.
