"""Helpers for compiling the public Parse API contract into internal requests."""

from __future__ import annotations

from cortex_auth import AuthorizationService, CallerContext
from cortex_contracts import (
    DownloadDisposition,
    ParseInputKind,
    ParseJobRequest,
    ParseJobSubmitRequest,
    ParseSource,
    ParseSubmitRequest,
    ParseSyncRequest,
)
from cortex_db import CortexUnitOfWork
from cortex_parse import ParseRequestCompiler
from cortex_storage import StorageService

from .storage import build_resource_context, get_object_record


async def compile_parse_sync_request(
    *,
    payload: ParseSubmitRequest,
    caller: CallerContext,
    auth_service: AuthorizationService,
    storage_service: StorageService,
    compiler: ParseRequestCompiler,
    uow: CortexUnitOfWork,
    request_id: str | None,
) -> ParseSyncRequest:
    resolved_source = await _resolve_source(
        payload=payload,
        caller=caller,
        auth_service=auth_service,
        storage_service=storage_service,
        uow=uow,
        request_id=request_id,
    )
    return compiler.compile_sync(payload, resolved_source=resolved_source)


async def compile_parse_job_request(
    *,
    payload: ParseJobSubmitRequest,
    caller: CallerContext,
    auth_service: AuthorizationService,
    storage_service: StorageService,
    compiler: ParseRequestCompiler,
    uow: CortexUnitOfWork,
    request_id: str | None,
) -> ParseJobRequest:
    resolved_source = await _resolve_source(
        payload=payload,
        caller=caller,
        auth_service=auth_service,
        storage_service=storage_service,
        uow=uow,
        request_id=request_id,
    )
    return compiler.compile_job(payload, resolved_source=resolved_source)


async def _resolve_source(
    *,
    payload: ParseSubmitRequest | ParseJobSubmitRequest,
    caller: CallerContext,
    auth_service: AuthorizationService,
    storage_service: StorageService,
    uow: CortexUnitOfWork,
    request_id: str | None,
) -> ParseSource | None:
    source = payload.source
    if not source.object_id:
        return None

    record = await get_object_record(uow, source.object_id)
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="storage:download",
        request_id=request_id,
        resource=build_resource_context(storage_service, record),
    )
    signed = await storage_service.create_download_url(
        uow=uow,
        object_id=record.object_id,
        ttl_seconds=900,
        disposition=DownloadDisposition.INLINE,
    )
    resolved_kind = source.kind or ParseInputKind.OBJECT
    locator = signed.url
    return ParseSource(
        input_kind=resolved_kind,
        object_id=record.object_id,
        url=locator if locator.startswith(("http://", "https://")) else None,
        uri=None if locator.startswith(("http://", "https://")) else locator,
        filename=source.filename or record.filename,
        canonical_url=source.canonical_url,
        expected_content_type=source.mime_type or record.content_type,
    )
