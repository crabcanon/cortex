"""Storage upload, metadata, and download endpoints."""

import json
from typing import Annotated

from cortex_auth import AuthorizationService, CallerContext
from cortex_common import CortexError, ValidationError
from cortex_contracts import (
    AccessPolicy,
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
from fastapi import APIRouter, Body, Depends, File, Form, Path, Query, Request, UploadFile, status

from ..dependencies.auth import get_current_caller
from ..dependencies.runtime import get_auth_service, get_storage_service, get_uow
from ..services.storage import build_resource_context, get_object_record

router = APIRouter(prefix="/v1/storage", tags=["Storage"])
_DIRECT_UPLOAD_CHUNK_SIZE = 1024 * 1024


def _parse_metadata_json(raw_value: str | None) -> dict[str, str]:
    if raw_value is None or not raw_value.strip():
        return {}
    payload = _parse_json_object(raw_value, field_name="metadata_json")
    return {str(key): str(value) for key, value in payload.items()}


def _parse_access_policy_json(raw_value: str | None) -> AccessPolicy | None:
    if raw_value is None or not raw_value.strip():
        return None
    payload = _parse_json_object(raw_value, field_name="access_policy_json")
    try:
        return AccessPolicy.model_validate(payload)
    except ValueError as exc:
        raise ValidationError("access_policy_json must match the AccessPolicy schema.") from exc


def _parse_tags(raw_value: str | None) -> list[str]:
    if raw_value is None or not raw_value.strip():
        return []
    stripped = raw_value.strip()
    if stripped.startswith("["):
        parsed = _parse_json_value(stripped, field_name="tags")
        if not isinstance(parsed, list):
            raise ValidationError("tags must be a JSON array or a comma-separated string.")
        return [str(item).strip() for item in parsed if str(item).strip()]
    return [item.strip() for item in stripped.split(",") if item.strip()]


def _parse_json_object(raw_value: str, *, field_name: str) -> dict[str, object]:
    parsed = _parse_json_value(raw_value, field_name=field_name)
    if not isinstance(parsed, dict):
        raise ValidationError(f"{field_name} must be a JSON object string.")
    return parsed


def _parse_json_value(raw_value: str, *, field_name: str) -> object:
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{field_name} must contain valid JSON.") from exc


async def _read_limited_upload_file(file: UploadFile, *, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total_size = 0
    while True:
        chunk = await file.read(_DIRECT_UPLOAD_CHUNK_SIZE)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_bytes:
            raise CortexError(
                code="direct_upload_too_large",
                detail=(
                    "Direct file upload exceeds the configured small-file limit. "
                    "Use the presigned upload-session flow for larger files."
                ),
                status_code=413,
                extra={
                    "max_size_bytes": max_bytes,
                    "actual_size_bytes": total_size,
                },
            )
        chunks.append(chunk)
    return b"".join(chunks)


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
    "/files",
    response_model=StorageObject,
    status_code=status.HTTP_201_CREATED,
    operation_id="uploadSmallFile",
    summary="Upload a small file",
    description=(
        "Upload a small file directly through the Cortex API. This endpoint is optimized for "
        "Swagger UI, local testing, and small files; use upload sessions for large files or "
        "production high-throughput transfers."
    ),
)
async def upload_small_file(
    request: Request,
    file: Annotated[
        UploadFile,
        File(
            description=(
                "File content to upload. Cortex derives filename, content type, and size from "
                "the multipart part."
            ),
        ),
    ],
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
    metadata_json: Annotated[
        str | None,
        Form(
            description="Optional JSON object string for object metadata. Best default: `{}`.",
            examples=['{"source":"swagger-demo","document_type":"guide"}'],
        ),
    ] = None,
    access_policy_json: Annotated[
        str | None,
        Form(
            description=(
                "Optional JSON object string matching AccessPolicy. "
                "Best default: omit for tenant_private."
            ),
            examples=['{"access_level":"tenant_shared"}'],
        ),
    ] = None,
    tags: Annotated[
        str | None,
        Form(
            description=(
                "Optional comma-separated tags or JSON array string. Best default: empty."
            ),
            examples=["docs,product"],
        ),
    ] = None,
    checksum_sha256: Annotated[
        str | None,
        Form(
            description=(
                "Optional lowercase SHA-256 checksum. Cortex verifies it before committing "
                "object metadata when provided."
            ),
            pattern=r"^[0-9a-f]{64}$",
            examples=["a" * 64],
        ),
    ] = None,
) -> StorageObject:
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="storage:write",
        request_id=getattr(request.state, "request_id", None),
    )
    content = await _read_limited_upload_file(
        file,
        max_bytes=storage_service.direct_upload_max_bytes,
    )
    return await storage_service.upload_small_file(
        uow=uow,
        caller=caller,
        filename=file.filename or "object.bin",
        content=content,
        content_type=file.content_type,
        checksum_sha256=checksum_sha256,
        metadata=_parse_metadata_json(metadata_json),
        access_policy=_parse_access_policy_json(access_policy_json),
        tags=_parse_tags(tags),
    )


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
        "Return the stored metadata, current version reference, and access policy for one object."
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
