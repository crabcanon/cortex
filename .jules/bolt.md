## YYYY-MM-DD - [Optimize sequence calculation for job events]
**Learning:** [Calculating the next sequence number by loading an entire list of events into memory (e.g. up to 1000 events) is an inefficient O(N) memory allocation operation. Doing this for every event insertion creates a massive and unnecessary bottleneck.]
**Action:** [Use optimized database aggregations, such as `JobEventRepository.get_max_sequence_no` utilizing `func.max()`, to reduce the O(N) loading operation to a highly efficient O(1) bandwidth query.]
