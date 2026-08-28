## 2024-08-28 - [Optimize next sequence calculation using SQL aggregation]
**Learning:** Loading up to 1000 job event objects into memory just to find the max sequence number is very inefficient and causes unnecessary memory pressure and slowdowns.
**Action:** Use SQL aggregation (`func.max()`) to calculate the next sequence number directly at the database level instead of loading full object lists into memory.
