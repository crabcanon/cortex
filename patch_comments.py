import re

files_to_patch = [
    'packages/parse/src/cortex_parse/jobs.py',
    'packages/synthesis/src/cortex_synthesis/jobs.py',
    'packages/evaluation/src/cortex_evaluation/jobs.py',
    'packages/knowledge/src/cortex_knowledge/jobs.py',
    'apps/api/src/cortex_api/services/jobs.py'
]

for filepath in files_to_patch:
    with open(filepath, 'r') as f:
        content = f.read()

    content = re.sub(
        r'(\s+)max_seq = await uow\.job_events\.get_max_sequence_no\(',
        r'\1# BOLT OPTIMIZATION: Use SQL MAX aggregation instead of loading the entire list into memory.\1max_seq = await uow.job_events.get_max_sequence_no(',
        content
    )
    with open(filepath, 'w') as f:
        f.write(content)
