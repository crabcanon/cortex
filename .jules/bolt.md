## 2024-05-13 - Fast Bulk Inserts
**Learning:** Adding multiple records individually via `session.add(model)` followed by `session.flush()` and `session.refresh(model)` inside a loop triggers N+1 queries.
**Action:** Use `session.add_all(models)` for bulk inserts to optimize database interactions. For Cortex repositories, since IDs are often generated client-side with `new_prefixed_id`, we can avoid `refresh()` for bulk operations if we don't need server-generated defaults back.
