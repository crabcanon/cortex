## YYYY-MM-DD - Optimize bulk database inserts
**Learning:** Sequential individual record inserts (`session.add()`) in `for` loops (N+1 inserts) can cause severe performance bottlenecks during document parsing and persistence where a single document can have thousands of chunks.
**Action:** Use `add_many()` repository methods paired with `session.add_all()` to efficiently batch inserts in a single database roundtrip, significantly reducing persistence latency.
