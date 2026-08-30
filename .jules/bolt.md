## YYYY-MM-DD - [Optimize next sequence generation using SQL aggregation]
**Learning:** [Using `list_for_job` with a limit of 1000 just to calculate the next sequence number by accessing the last element causes unnecessary memory overhead and database load. A memory note indicates `JobEventRepository` provides an optimized `get_max_sequence_no(job_id)` method using SQL aggregation (`func.max`).]
**Action:** [Use the optimized SQL aggregation method to calculate sequence numbers instead of loading large lists of entities into application memory.]
