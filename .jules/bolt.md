## 2024-05-24 - Bulk insertion of records

**Learning:** Avoid N+1 query patterns during bulk insertions by utilizing `add_many()` repository methods which leverage `session.add_all()` to insert models efficiently without triggering per-record `session.refresh()` queries. The application typically generates primary keys using `cortex_common.new_prefixed_id` at the service layer, enabling repository `add_many` methods to return `None` and skip `session.refresh()` for improved bulk insertion performance.
**Action:** When inserting multiple models iteratively inside a for-loop, add a bulk insertion method to the corresponding repository (`add_many`), and change the service logic to perform a single call to `add_many`.
