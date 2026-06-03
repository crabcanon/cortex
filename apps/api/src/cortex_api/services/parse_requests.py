"""Helpers for compiling the public Parse API contract into internal requests."""

from __future__ import annotations

from cortex_auth import AuthorizationService, CallerContext
from cortex_contracts import (
    DownloadDisposition,
    ParseInputKind,
    ParseJobRequest,
    ParseJobSubmitRequest,
    ParseSource,
    ParseSourceInput,
    ParseSubmitRequest,
    ParseSyncRequest,
)
from cortex_db import CortexUnitOfWork
from cortex_parse import ParseRequestCompiler
from cortex_storage import StorageService

from .storage import build_resource_context, get_object_record

SYNC_OBJECT_DOWNLOAD_TTL_SECONDS = 900
ASYNC_OBJECT_DOWNLOAD_TTL_SECONDS = 3600


async def compile_parse_sync_requests(
    *,
    payload: ParseSubmitRequest,
    caller: CallerContext,
    auth_service: AuthorizationService,
    storage_service: StorageService,
    compiler: ParseRequestCompiler,
    uow: CortexUnitOfWork,
    request_id: str | None,
) -> list[ParseSyncRequest]:
    compiled: list[ParseSyncRequest] = []
    for locator in payload.sources:
        source_input = compiler.source_input_from_locator(locator)
        resolved_source = await _resolve_source(
            source_input=source_input,
            caller=caller,
            auth_service=auth_service,
            storage_service=storage_service,
            uow=uow,
            request_id=request_id,
            download_ttl_seconds=SYNC_OBJECT_DOWNLOAD_TTL_SECONDS,
        )
        compiled.append(
            compiler.compile_sync(
                payload,
                source_input,
                resolved_source=resolved_source,
            )
        )
    return compiled


async def compile_parse_job_requests(
    *,
    payload: ParseJobSubmitRequest,
    caller: CallerContext,
    auth_service: AuthorizationService,
    storage_service: StorageService,
    compiler: ParseRequestCompiler,
    uow: CortexUnitOfWork,
    request_id: str | None,
) -> list[ParseJobRequest]:
    compiled: list[ParseJobRequest] = []
    for locator in payload.sources:
        source_input = compiler.source_input_from_locator(locator)
        resolved_source = await _resolve_source(
            source_input=source_input,
            caller=caller,
            auth_service=auth_service,
            storage_service=storage_service,
            uow=uow,
            request_id=request_id,
            download_ttl_seconds=ASYNC_OBJECT_DOWNLOAD_TTL_SECONDS,
        )
        compiled.append(
            compiler.compile_job(
                payload,
                source_input,
                resolved_source=resolved_source,
            )
        )
    return compiled


async def _resolve_source(
    *,
    source_input: ParseSourceInput,
    caller: CallerContext,
    auth_service: AuthorizationService,
    storage_service: StorageService,
    uow: CortexUnitOfWork,
    request_id: str | None,
    download_ttl_seconds: int,
) -> ParseSource | None:
    if not source_input.object_id:
        return None

    record = await get_object_record(uow, source_input.object_id)
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
        ttl_seconds=download_ttl_seconds,
        disposition=DownloadDisposition.INLINE,
    )
    locator = signed.url
    return ParseSource(
        input_kind=ParseInputKind.OBJECT,
        object_id=record.object_id,
        url=locator if locator.startswith(("http://", "https://")) else None,
        uri=None if locator.startswith(("http://", "https://")) else locator,
        filename=source_input.filename or record.filename,
        canonical_url=source_input.canonical_url,
        expected_content_type=source_input.mime_type or record.content_type,
    )
