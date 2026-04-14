"""Storage upload, metadata, and download endpoints."""

from typing import Annotated

from cortex_auth import AuthorizationService, CallerContext
from cortex_contracts import (
    DownloadDisposition,
    DownloadUrlResponse,
    StorageObject,
    StorageUploadCompleteRequest,
    StorageUploadCreateRequest,
    StorageUploadSession,
)
from cortex_db import CortexUnitOfWork
from cortex_storage import StorageService
from fastapi import APIRouter, Depends, Header, Query, Request, status

from ..dependencies.auth import get_current_caller
from ..dependencies.runtime import get_auth_service, get_storage_service, get_uow
from ..services.storage import build_resource_context, get_object_record

router = APIRouter(prefix="/v1/storage", tags=["Storage"])


@router.post(
    "/uploads",
    response_model=StorageUploadSession,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate an upload session / initialize upload session",
)
async def create_upload_session(
    request: Request,
    payload: StorageUploadCreateRequest,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> StorageUploadSession:
    del idempotency_key
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="storage:write",
        request_id=getattr(request.state, "request_id", None),
    )
    return await storage_service.create_upload_session(uow=uow, caller=caller, request=payload)


@router.post(
    "/uploads/{upload_id}/complete",
    response_model=StorageObject,
    summary="Complete an upload session / complete upload session",
)
async def complete_upload_session(
    request: Request,
    upload_id: str,
    payload: StorageUploadCompleteRequest,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
) -> StorageObject:
    record = await get_object_record(uow, upload_id)
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="storage:write",
        request_id=getattr(request.state, "request_id", None),
        resource=build_resource_context(storage_service, record),
    )
    return await storage_service.complete_upload_session(
        uow=uow,
        upload_id=upload_id,
        request=payload,
    )


@router.get(
    "/objects/{object_id}",
    response_model=StorageObject,
    summary="Get object metadata / get object metadata",
)
async def get_storage_object(
    request: Request,
    object_id: str,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
) -> StorageObject:
    record = await get_object_record(uow, object_id)
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="storage:read",
        request_id=getattr(request.state, "request_id", None),
        resource=build_resource_context(storage_service, record),
    )
    return await storage_service.get_object(uow=uow, object_id=object_id)


@router.get(
    "/objects/{object_id}/download-url",
    response_model=DownloadUrlResponse,
    summary="Create a download URL for an object / create download url",
)
async def create_download_url(
    request: Request,
    object_id: str,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
    ttl_seconds: Annotated[int, Query(ge=60, le=86400)] = 900,
    disposition: Annotated[DownloadDisposition, Query()] = DownloadDisposition.ATTACHMENT,
) -> DownloadUrlResponse:
    record = await get_object_record(uow, object_id)
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="storage:download",
        request_id=getattr(request.state, "request_id", None),
        resource=build_resource_context(storage_service, record),
    )
    return await storage_service.create_download_url(
        uow=uow,
        object_id=object_id,
        ttl_seconds=ttl_seconds,
        disposition=disposition,
    )
