## 2024-05-19 - Use Aggregates for Max Sequences
**Learning:** Loading lists of database records into memory to find the max sequence number (e.g., `list_for_job(...)` to extract `existing_events[-1].sequence_no`) is an O(N) memory anti-pattern and can cause significant overhead.
**Action:** Implemented `get_max_sequence_no` in the Repository layer that leverages `select(func.coalesce(func.max(...)))` for an efficient O(1) database aggregation instead of doing this application-side. Will utilize SQL aggregates explicitly for metrics going forward.
