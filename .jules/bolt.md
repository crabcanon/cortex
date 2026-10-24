# Bolt's Journal

## YYYY-MM-DD - [Optimize Document Insertion Performance]
**Learning:** In the database repository, `session.add_all()` is a wrapper around `.add()`, and both defer SQL execution until `flush()`. However, calling an entity repository's async `.add()` method within a loop is an anti-pattern because the repository implementation explicitly calls `await self._session.flush()` inside the `.add()` method, triggering an N+1 query scenario where a separate roundtrip to the DB is made for each item.
**Action:** When inserting multiple records, explicitly build a list of models and execute a single `await session.flush()` using a dedicated `.add_many()` method in the repository to batch the insertions and skip unnecessary single-row refreshes.
