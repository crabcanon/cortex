"""Job inspection and control endpoints."""

from typing import Annotated

from cortex_auth import AuthorizationService, ResourceAuthorizationContext
from cortex_auth.models import CallerContext
from cortex_contracts import JobEvent, JobStatusDetail
from cortex_db import CortexUnitOfWork
from cortex_domain import AccessLevel
from fastapi import APIRouter, Depends, Query, Request

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


@router.get("/{job_id}", response_model=JobStatusDetail, summary="Get job status")
async def get_job(
    request: Request,
    job_id: str,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
) -> JobStatusDetail:
    return await _authorize_job(
        job_id=job_id,
        permission_key="jobs:read",
        caller=caller,
        auth_service=auth_service,
        uow=uow,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/{job_id}/events", response_model=list[JobEvent], summary="List job events")
async def get_job_events(
    request: Request,
    job_id: str,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
    limit: int = Query(default=100, ge=1, le=500),
) -> list[JobEvent]:
    await _authorize_job(
        job_id=job_id,
        permission_key="jobs:read",
        caller=caller,
        auth_service=auth_service,
        uow=uow,
        request_id=getattr(request.state, "request_id", None),
    )
    return await list_job_events(uow, job_id, limit=limit)


@router.post(
    "/{job_id}/cancel",
    response_model=JobStatusDetail,
    status_code=202,
    summary="Cancel a job",
)
async def post_job_cancel(
    request: Request,
    job_id: str,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
) -> JobStatusDetail:
    await _authorize_job(
        job_id=job_id,
        permission_key="jobs:cancel",
        caller=caller,
        auth_service=auth_service,
        uow=uow,
        request_id=getattr(request.state, "request_id", None),
    )
    return await cancel_job(uow, job_id)
