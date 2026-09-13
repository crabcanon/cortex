The issue is that there's an N+1 issue in generating the next `sequence_no` for `JobEventRepository`.
Specifically, `packages/parse/src/cortex_parse/jobs.py`, `packages/synthesis/src/cortex_synthesis/jobs.py`, `packages/evaluation/src/cortex_evaluation/jobs.py`, and `packages/knowledge/src/cortex_knowledge/jobs.py`, and `apps/api/src/cortex_api/services/jobs.py` all use `list_for_job` with `limit=1000` just to find the next `sequence_no` for a `job_id`. This loads up to 1000 objects in memory each time just to calculate max(sequence_no).

Instead, as hinted in the memory, I should create a `get_max_sequence_no` function in `JobEventRepository` to aggregate using `func.max`:
```python
    async def get_max_sequence_no(self, job_id: str) -> int:
        result = await self._session.execute(
            select(func.max(JobEventModel.sequence_no)).where(JobEventModel.job_id == job_id)
        )
        max_seq = result.scalar()
        return max_seq or 0
```

I will need to import `func` from sqlalchemy: `from sqlalchemy import desc, func, select, text, delete`

I will add this to `packages/db/src/cortex_db/repositories.py` and then update the 5 usages to:
```python
        max_sequence = await uow.job_events.get_max_sequence_no(job_id)
        next_sequence = max_sequence + 1
```

Does this sound correct?
