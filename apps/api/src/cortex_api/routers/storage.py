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
from cortex_contracts.openapi_examples import (
    OBJECT_ID_EXAMPLE,
    STORAGE_UPLOAD_COMPLETE_REQUEST_EXAMPLES,
    STORAGE_UPLOAD_CREATE_REQUEST_EXAMPLES,
    TTL_SECONDS_EXAMPLE,
    UPLOAD_ID_EXAMPLE,
)
from cortex_db import CortexUnitOfWork
from cortex_storage import StorageService
from fastapi import APIRouter, Body, Depends, Path, Query, Request, status

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
    description=(
        "Create a signed upload session for a new object. "
        "The caller supplies file identity plus business metadata, while Cortex infers "
        "content type when possible and decides whether multipart is needed."
    ),
)
async def create_upload_session(
    request: Request,
    payload: Annotated[
        StorageUploadCreateRequest,
        Body(
            openapi_examples=STORAGE_UPLOAD_CREATE_REQUEST_EXAMPLES,
            description=(
                "Upload session creation request. `filename` is required. Cortex infers "
                "`content_type` from `filename` when omitted, uses `size_bytes` when available "
                "to decide single-part vs multipart, and manages bucket/object-key routing "
                "internally."
            ),
        ),
    ],
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
) -> StorageUploadSession:
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
    description=(
        "Finalize a single-part or multipart upload session after the object-store transfer has "
        "succeeded. This step is required because Cortex must verify the uploaded object, recover "
        "provider metadata, and commit the final object/version records."
    ),
)
async def complete_upload_session(
    request: Request,
    uploadId: Annotated[
        str,
        Path(
            description="Upload session identifier returned by `/v1/storage/uploads`.",
            examples=[UPLOAD_ID_EXAMPLE],
        ),
    ],
    payload: Annotated[
        StorageUploadCompleteRequest,
        Body(
            openapi_examples=STORAGE_UPLOAD_COMPLETE_REQUEST_EXAMPLES,
            description=(
                "Upload completion request. Use the single-part "
                "example when no multipart parts were issued."
            ),
        ),
    ],
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
    description=(
        "Return the stored metadata, current version reference, "
        "and access policy for one object."
    ),
)
async def get_storage_object(
    request: Request,
    objectId: Annotated[
        str,
        Path(
            description="Storage object identifier returned by upload or search flows.",
            examples=[OBJECT_ID_EXAMPLE],
        ),
    ],
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
    description="Create a time-limited signed download URL for an object.",
)
async def create_download_url(
    request: Request,
    objectId: Annotated[
        str,
        Path(
            description="Storage object identifier to download.",
            examples=[OBJECT_ID_EXAMPLE],
        ),
    ],
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
    ttl_seconds: Annotated[
        int,
        Query(
            ge=60,
            le=86400,
            description="Signed URL lifetime in seconds. Best default: 900 (15 minutes).",
            examples=[TTL_SECONDS_EXAMPLE],
        ),
    ] = 900,
    disposition: Annotated[
        DownloadDisposition,
        Query(
            description=(
                "Suggested content disposition. Best default: "
                "`attachment`; use `inline` for browser preview."
            ),
            examples=["attachment"],
        ),
    ] = DownloadDisposition.ATTACHMENT,
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
