## YYYY-MM-DD - Optimize bulk database inserts
**Learning:** Sequential `.add()` combined with `flush()` and `refresh()` triggers N+1 per-record queries during bulk insertions in SQLAlchemy.
**Action:** Use `.add_all()` without `refresh()` for bulk insertions to eliminate N+1 queries.
