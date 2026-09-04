## YYYY-MM-DD - [Optimize Document/Parse Runs Bulk Inserts]
**Learning:** N+1 query patterns during bulk insertions in loops create significant overhead because of sequential queries and per-record session refreshes.
**Action:** Implemented and utilized `add_many` repository methods via `session.add_all` to insert objects concurrently, dropping N+1 queries to boost performance.
