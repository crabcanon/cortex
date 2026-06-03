## 2023-10-27 - [Fix] Fix Sequence Max Computation using MAX Query
**Learning:** Found sequence tracking issue where arrays list_for_job limited at 1000 items were accessed using existing_events[-1].sequence_no, leading to out of memory/bugs with big limits and slow database fetches.
**Action:** Always fetch `max()` directly using an aggregation query via SQLAlchemy in repositories instead of large array fetches.
