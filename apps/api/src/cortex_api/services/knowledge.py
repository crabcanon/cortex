"""Knowledge API helpers."""

from cortex_auth import ResourceAuthorizationContext
from cortex_db import CortexUnitOfWork
from cortex_domain import DatasetRecord
from cortex_knowledge import KnowledgeDatasetService


async def get_dataset_record(
    knowledge_service: KnowledgeDatasetService,
    uow: CortexUnitOfWork,
    dataset_id: str,
) -> DatasetRecord:
    return await knowledge_service.get_dataset_record(uow=uow, dataset_id=dataset_id)


def build_resource_context(
    knowledge_service: KnowledgeDatasetService,
    record: DatasetRecord,
) -> ResourceAuthorizationContext:
    return ResourceAuthorizationContext(**knowledge_service.build_access_context(record))
