## YYYY-MM-DD - Bulk Insert Optimization for Parsing Service
**Learning:** The document persistence layer was calling `session.add()` and `session.refresh()` inside loops for chunks, tags, artifacts, and attempts, leading to an N+1 query problem during bulk insertion of parsed document pieces.
**Action:** When inserting multiple related child records (like document chunks or tags), use `session.add_all()` without `session.refresh()` to skip unnecessary SELECT queries after INSERT. Exposed `add_many()` methods on repositories where bulk creation is common.
