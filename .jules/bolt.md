## 2024-04-19 - Optimize sequence max calculation
**Learning:** Avoid fetching whole rows in memory using `list_for_job(...)` simply to find the max `sequence_no`. This is an O(n) fetching operation and a common codebase-specific anti-pattern. Instead, leverage `func.max` in the database repository to push this calculation to the SQL query.
**Action:** Always search for operations taking the `[-1]` of a `list_*` method on repositories and replace them with specific aggregation queries in the repository.
