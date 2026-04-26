"""Synthesis endpoints."""

from typing import Annotated

from cortex_auth import AuthorizationService, CallerContext, ResourceAuthorizationContext
from cortex_contracts import (
    JobStatusDetail,
    SynthesisEngineList,
    SynthesisJobAccepted,
    SynthesisJobSubmitRequest,
    SynthesisRunResult,
    SynthesisSyncRequest,
)
from cortex_contracts.openapi_examples import (
    IDEMPOTENCY_KEY_EXAMPLE,
    SYNTHESIS_JOB_REQUEST_EXAMPLES,
    SYNTHESIS_SYNC_REQUEST_EXAMPLES,
)
from cortex_db import CortexUnitOfWork
from cortex_domain import AccessLevel
from cortex_synthesis import SynthesisJobControlService, SynthesisService
from fastapi import APIRouter, Body, Depends, Header, Request, Response, status

from ..dependencies.auth import get_current_caller
from ..dependencies.runtime import (
    get_auth_service,
    get_synthesis_job_service,
    get_synthesis_service,
    get_uow,
)
from ..services.jobs import get_job_status

router = APIRouter(prefix="/v1/synthesis", tags=["Synthesis"])


async def _authorize_synthesis_job(
    *,
    request: Request,
    job_id: str,
    caller: CallerContext,
    auth_service: AuthorizationService,
    uow: CortexUnitOfWork,
) -> JobStatusDetail:
    job_record = await uow.jobs.get(job_id)
    job = await get_job_status(uow, job_id)
    if job_record is None:
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
        permission_key="synthesis:read",
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
    response_model=SynthesisEngineList,
    operation_id="listSynthesisEngines",
    summary="List synthesis engines",
    description=(
        "Returns the currently registered synthesis engines, supported synthesis types, "
        "supported source kinds, and output format hints."
    ),
)
async def list_synthesis_engines(
    request: Request,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    synthesis_service: Annotated[SynthesisService, Depends(get_synthesis_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
) -> SynthesisEngineList:
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="synthesis:read",
        request_id=getattr(request.state, "request_id", None),
    )
    return synthesis_service.list_engines()


@router.post(
    "/sync",
    response_model=SynthesisRunResult,
    operation_id="runSynthesisSync",
    summary="Execute a synchronous synthesis run",
    description=(
        "Runs a small synthesis workload synchronously. Recommended for preview generation, "
        "quality-gate tuning, and low-cardinality source samples."
    ),
)
async def run_synthesis_sync(
    request: Request,
    payload: Annotated[
        SynthesisSyncRequest,
        Body(
            openapi_examples=SYNTHESIS_SYNC_REQUEST_EXAMPLES,
            description=(
                "Unified synthesis request body. Required: `synthesis_type` and `source`. "
                "`engine_id` defaults to `auto`."
            ),
        ),
    ],
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    synthesis_service: Annotated[SynthesisService, Depends(get_synthesis_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
) -> SynthesisRunResult:
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="synthesis:write",
        request_id=getattr(request.state, "request_id", None),
    )
    return await synthesis_service.run(payload)


@router.post(
    "/jobs",
    response_model=SynthesisJobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="createSynthesisJob",
    summary="Submit an asynchronous synthesis job",
    description=(
        "Queues a longer-running synthesis workload and returns a Cortex job handle for "
        "polling and result retrieval."
    ),
)
async def create_synthesis_job(
    request: Request,
    payload: Annotated[
        SynthesisJobSubmitRequest,
        Body(
            openapi_examples=SYNTHESIS_JOB_REQUEST_EXAMPLES,
            description=(
                "Async synthesis job request. Use this for larger synthetic dataset creation "
                "or batch enrichment workloads."
            ),
        ),
    ],
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    synthesis_service: Annotated[SynthesisService, Depends(get_synthesis_service)],
    synthesis_job_service: Annotated[
        SynthesisJobControlService, Depends(get_synthesis_job_service)
    ],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            description="Optional idempotency key for asynchronous synthesis job submission.",
            examples=[IDEMPOTENCY_KEY_EXAMPLE],
        ),
    ] = None,
) -> SynthesisJobAccepted:
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="synthesis:write",
        request_id=getattr(request.state, "request_id", None),
    )
    resolved = synthesis_service.resolve_request(payload)
    return await synthesis_job_service.submit(
        uow=uow,
        caller=caller,
        request=resolved.request,
        idempotency_key=idempotency_key,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "/jobs/{jobId}/result",
    response_model=SynthesisRunResult | JobStatusDetail,
    operation_id="getSynthesisResult",
    responses={409: {"model": JobStatusDetail}},
    summary="Get a completed synthesis result",
    description=(
        "Returns the completed synthesis result when the async job succeeds, or a 409 job "
        "status payload while work is still in progress."
    ),
)
async def get_synthesis_result(
    request: Request,
    response: Response,
    jobId: str,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    synthesis_job_service: Annotated[
        SynthesisJobControlService, Depends(get_synthesis_job_service)
    ],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
) -> SynthesisRunResult | JobStatusDetail:
    job = await _authorize_synthesis_job(
        request=request,
        job_id=jobId,
        caller=caller,
        auth_service=auth_service,
        uow=uow,
    )
    result = await synthesis_job_service.get_completed_result(uow=uow, job_id=jobId)
    if result is None:
        response.status_code = status.HTTP_409_CONFLICT
        return job
    return result
