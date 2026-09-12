## 2024-05-15 - Optimize sequence calculation in JobEventRepository
**Learning:** Loading entire lists of events into memory just to calculate `next_sequence = existing_events[-1].sequence_no + 1 if existing_events else 1` causes performance and memory issues, particularly for jobs with many events.
**Action:** Use SQL aggregation `get_max_sequence_no` in repositories to avoid loading full collections into memory when calculating sequence numbers.
