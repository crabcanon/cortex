## 2025-02-18 - Optimize Maximum Sequence Number Lookup in Job Event Repository

**Learning:** Previously, finding the maximum sequence number for job events involved loading up to 1000 event records from the database into memory and accessing the last element (`existing_events[-1].sequence_no`). This loaded unnecessary records and scaled poorly ($O(n)$ up to the limit).

**Action:** Replaced the list retrieval approach with an aggregate SQL query `select(func.coalesce(func.max(JobEventModel.sequence_no), 0))` in `JobEventRepository.get_max_sequence_no(job_id)`. This pushes the computation to the database layer, executing in $O(1)$ efficiency without fetching unnecessary rows, improving both performance and memory usage.
