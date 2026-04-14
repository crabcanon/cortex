"""Parse engine catalog and synchronous parse endpoints."""

from typing import Annotated

from cortex_auth import AuthorizationService, CallerContext, ResourceAuthorizationContext
from cortex_contracts import (
    JobAccepted,
    JobStatusDetail,
    ParseEngineList,
    ParseJobRequest,
    ParseResult,
    ParserProfileList,
    ParseSyncRequest,
)
from cortex_db import CortexUnitOfWork
from cortex_domain import AccessLevel
from cortex_parse import ParseJobControlService, ParseService
from fastapi import APIRouter, Depends, Header, Request, Response, status

from ..dependencies.auth import get_current_caller
from ..dependencies.runtime import (
    get_auth_service,
    get_parse_job_service,
    get_parse_service,
    get_uow,
)
from ..services.jobs import get_job_status

router = APIRouter(prefix="/v1/parse", tags=["Parse"])


async def _authorize_parse_job(
    *,
    request: Request,
    job_id: str,
    caller: CallerContext,
    auth_service: AuthorizationService,
    uow: CortexUnitOfWork,
) -> JobStatusDetail:
    job_record = await uow.jobs.get(job_id)
    job = await get_job_status(uow, job_id)
    if job_record is None:  # pragma: no cover - guarded by get_job_status
        return job
    resource = ResourceAuthorizationContext(
        tenant_id=job_record.tenant_id,
        resource_type="job",
        resource_id=job_id,
        access_level=AccessLevel.TENANT_PRIVATE,
        attributes={"job_type": job_record.job_type.value},
    )
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="parse:read",
        request_id=getattr(request.state, "request_id", None),
        resource=resource,
    )
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="jobs:read",
        request_id=getattr(request.state, "request_id", None),
        resource=resource,
    )
    return job


@router.get(
    "/engines",
    response_model=ParseEngineList,
    summary="List parse engines / list parse engines",
)
async def list_parse_engines(
    request: Request,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    parse_service: Annotated[ParseService, Depends(get_parse_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
) -> ParseEngineList:
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="parse:read",
        request_id=getattr(request.state, "request_id", None),
    )
    return parse_service.list_engines()


@router.get(
    "/profiles",
    response_model=ParserProfileList,
    summary="List parser profiles / list parser profiles",
)
async def list_parser_profiles(
    request: Request,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    parse_service: Annotated[ParseService, Depends(get_parse_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
) -> ParserProfileList:
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="parse:read",
        request_id=getattr(request.state, "request_id", None),
    )
    return parse_service.list_profiles()


@router.post(
    "/sync",
    response_model=ParseResult,
    summary="Parse content synchronously / parse content synchronously",
)
async def parse_content_sync(
    request: Request,
    payload: ParseSyncRequest,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    parse_service: Annotated[ParseService, Depends(get_parse_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ParseResult:
    del idempotency_key
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="parse:write",
        request_id=getattr(request.state, "request_id", None),
    )
    return await parse_service.parse(uow=uow, caller=caller, request=payload)


@router.post(
    "/jobs",
    response_model=JobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit an async parse job / submit async parse job",
)
async def create_parse_job(
    request: Request,
    payload: ParseJobRequest,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    parse_job_service: Annotated[ParseJobControlService, Depends(get_parse_job_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> JobAccepted:
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="parse:write",
        request_id=getattr(request.state, "request_id", None),
    )
    return await parse_job_service.submit(
        uow=uow,
        caller=caller,
        request=payload,
        idempotency_key=idempotency_key,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "/jobs/{job_id}/result",
    response_model=ParseResult | JobStatusDetail,
    summary="Get parse job result / get parse job result",
)
async def get_parse_job_result(
    request: Request,
    response: Response,
    job_id: str,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    parse_job_service: Annotated[ParseJobControlService, Depends(get_parse_job_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
) -> ParseResult | JobStatusDetail:
    job = await _authorize_parse_job(
        request=request,
        job_id=job_id,
        caller=caller,
        auth_service=auth_service,
        uow=uow,
    )
    result = await parse_job_service.get_completed_result(uow=uow, job_id=job_id)
    if result is None:
        response.status_code = status.HTTP_202_ACCEPTED
        return job
    return result
