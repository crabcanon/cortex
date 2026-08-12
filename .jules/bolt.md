## YYYY-MM-DD - [Optimize Sequence Calculation]
**Learning:** Loading list_for_job just to calculate max sequence_no for job_events is an O(n) memory hit and query inefficiency, avoiding array access logic on lists.
**Action:** Use database aggregation (select(func.max(...))) directly rather than full object queries when counting or sequence generation logic requires determining sequence maximums.
