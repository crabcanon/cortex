"""Storage API helpers."""

from cortex_auth import ResourceAuthorizationContext
from cortex_common import NotFoundError
from cortex_db import CortexUnitOfWork
from cortex_domain import ObjectRecord
from cortex_storage import StorageService


async def get_object_record(uow: CortexUnitOfWork, object_id: str) -> ObjectRecord:
    record = await uow.objects.get(object_id)
    if record is None:
        raise NotFoundError(f"Object `{object_id}` was not found.")
    return record


def build_resource_context(
    storage_service: StorageService,
    record: ObjectRecord,
) -> ResourceAuthorizationContext:
    return ResourceAuthorizationContext(**storage_service.build_access_context(record))
