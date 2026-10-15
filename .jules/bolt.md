## YYYY-MM-DD - N+1 Insert Optimization
**Learning:** In SQLAlchemy with async repositories, looping `await repo.add()` triggers an explicit `flush()` and `refresh()` per record, causing a major bottleneck for large lists (like document chunks).
**Action:** Use an explicit `add_many()` method on repositories to insert a list of models, doing a single `session.flush()` at the end, and skipping `session.refresh()` unless the generated DB values are strictly necessary.
