
## 2024-05-18 - Bulk Insertion for Performance Optimization
**Learning:** Performing per-record insertion with `session.add()` and `session.refresh()` in loops creates an N+1 query pattern, which severely degrades performance when parsing large documents containing many tags, chunks, or artifacts.
**Action:** Utilize the repository's `add_many()` implementations which leverage `session.add_all()` to bulk insert models efficiently without triggering per-record DB refresh queries. Always batch records during iterative processing.
