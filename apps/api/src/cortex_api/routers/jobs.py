"""Job inspection and control endpoints."""

from typing import Annotated

from cortex_auth import AuthorizationService, ResourceAuthorizationContext
from cortex_auth.models import CallerContext
from cortex_contracts import JobEvent, JobStatusDetail
from cortex_contracts.openapi_examples import JOB_ID_EXAMPLE, LIMIT_EXAMPLE
from cortex_db import CortexUnitOfWork
from cortex_domain import AccessLevel
from fastapi import APIRouter, Depends, Path, Query, Request

from ..dependencies.auth import get_current_caller
from ..dependencies.runtime import get_auth_service, get_uow
from ..services.jobs import cancel_job, get_job_status, list_job_events

router = APIRouter(prefix="/v1/jobs", tags=["Jobs"])


async def _authorize_job(
    *,
    job_id: str,
    permission_key: str,
    caller: CallerContext,
    auth_service: AuthorizationService,
    uow: CortexUnitOfWork,
    request_id: str | None,
) -> JobStatusDetail:
    job_record = await uow.jobs.get(job_id)
    job = await get_job_status(uow, job_id)
    if job_record is None:  # pragma: no cover - guarded by get_job_status
        return job
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key=permission_key,
        request_id=request_id,
        resource=ResourceAuthorizationContext(
            tenant_id=job_record.tenant_id,
            resource_type="job",
            resource_id=job.job_id,
            access_level=AccessLevel.TENANT_PRIVATE,
            attributes={"job_type": job.job_type.value},
        ),
    )
    return job


@router.get(
    "/{jobId}",
    response_model=JobStatusDetail,
    operation_id="getJob",
    summary="Get job status",
    description=(
        "Return the current state, timestamps, and telemetry "
        "context for one long-running job."
    ),
)
async def get_job(
    request: Request,
    jobId: Annotated[
        str,
        Path(
            description=(
                "Job identifier returned by a create-job endpoint "
                "such as Parse, Add, Cognify, or Memify."
            ),
            examples=[JOB_ID_EXAMPLE],
        ),
    ],
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
) -> JobStatusDetail:
    return await _authorize_job(
        job_id=jobId,
        permission_key="jobs:read",
        caller=caller,
        auth_service=auth_service,
        uow=uow,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "/{jobId}/events",
    response_model=list[JobEvent],
    operation_id="listJobEvents",
    summary="List job events",
    description=(
        "Return the ordered event stream for one job, newest "
        "first according to the service implementation."
    ),
)
async def get_job_events(
    request: Request,
    jobId: Annotated[
        str,
        Path(
            description="Job identifier whose event stream should be returned.",
            examples=[JOB_ID_EXAMPLE],
        ),
    ],
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=500,
            description="Maximum number of events to return. Best default: 100.",
            examples=[LIMIT_EXAMPLE],
        ),
    ] = 100,
) -> list[JobEvent]:
    await _authorize_job(
        job_id=jobId,
        permission_key="jobs:read",
        caller=caller,
        auth_service=auth_service,
        uow=uow,
        request_id=getattr(request.state, "request_id", None),
    )
    return await list_job_events(uow, jobId, limit=limit)


@router.post(
    "/{jobId}/cancel",
    response_model=JobStatusDetail,
    status_code=202,
    operation_id="cancelJob",
    summary="Cancel a queued or running job",
    description=(
        "Request cancellation of a queued or running job and "
        "return the updated status snapshot."
    ),
)
async def post_job_cancel(
    request: Request,
    jobId: Annotated[
        str,
        Path(
            description="Job identifier to cancel.",
            examples=[JOB_ID_EXAMPLE],
        ),
    ],
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
) -> JobStatusDetail:
    await _authorize_job(
        job_id=jobId,
        permission_key="jobs:cancel",
        caller=caller,
        auth_service=auth_service,
        uow=uow,
        request_id=getattr(request.state, "request_id", None),
    )
    return await cancel_job(uow, jobId)
