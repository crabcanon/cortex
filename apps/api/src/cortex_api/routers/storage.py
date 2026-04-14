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
    operation_id="createUploadSession",
    summary="Initiate an upload session",
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
    "/uploads/{uploadId}/complete",
    response_model=StorageObject,
    operation_id="completeUploadSession",
    summary="Complete an upload session",
)
async def complete_upload_session(
    request: Request,
    uploadId: str,
    payload: StorageUploadCompleteRequest,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
) -> StorageObject:
    record = await get_object_record(uow, uploadId)
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="storage:write",
        request_id=getattr(request.state, "request_id", None),
        resource=build_resource_context(storage_service, record),
    )
    return await storage_service.complete_upload_session(
        uow=uow,
        upload_id=uploadId,
        request=payload,
    )


@router.get(
    "/objects/{objectId}",
    response_model=StorageObject,
    operation_id="getStorageObject",
    summary="Get object metadata",
)
async def get_storage_object(
    request: Request,
    objectId: str,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
) -> StorageObject:
    record = await get_object_record(uow, objectId)
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="storage:read",
        request_id=getattr(request.state, "request_id", None),
        resource=build_resource_context(storage_service, record),
    )
    return await storage_service.get_object(uow=uow, object_id=objectId)


@router.get(
    "/objects/{objectId}/download-url",
    response_model=DownloadUrlResponse,
    operation_id="createDownloadUrl",
    summary="Create a download URL for an object",
)
async def create_download_url(
    request: Request,
    objectId: str,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
    ttl_seconds: Annotated[int, Query(ge=60, le=86400)] = 900,
    disposition: Annotated[DownloadDisposition, Query()] = DownloadDisposition.ATTACHMENT,
) -> DownloadUrlResponse:
    record = await get_object_record(uow, objectId)
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="storage:download",
        request_id=getattr(request.state, "request_id", None),
        resource=build_resource_context(storage_service, record),
    )
    return await storage_service.create_download_url(
        uow=uow,
        object_id=objectId,
        ttl_seconds=ttl_seconds,
        disposition=disposition,
    )
