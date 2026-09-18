## YYYY-MM-DD - Replace N+1 queries with bulk insertions
**Learning:** During bulk insertions, inserting models one-by-one with `session.add()` inside loops triggers unnecessary individual `session.refresh()` queries and severely impairs performance (N+1 query pattern).
**Action:** Utilize repository `add_many()` methods that leverage `session.add_all()` to insert models efficiently without triggering per-record refresh queries. Generate primary keys upstream using `cortex_common.new_prefixed_id` to enable this pattern.
