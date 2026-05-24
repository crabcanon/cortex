## 2026-04-24 - Optimize backend DB access by avoiding memory loads
**Learning:** Found N+1 query-like inefficiencies in Job sequence number calculations by unnecessarily loading lists of entities just to calculate maximum values using python sequence indexing list[-1].
**Action:** Replaced these inefficient approaches with explicit SQL aggregation mapping `func.coalesce(func.max(...))` inside DB repository methods allowing calculations to happen efficiently in the database layer.
