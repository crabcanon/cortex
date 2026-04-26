"""Evaluation endpoints."""

from typing import Annotated

from cortex_auth import AuthorizationService, CallerContext, ResourceAuthorizationContext
from cortex_contracts import (
    EvalEngineList,
    EvalJobAccepted,
    EvalJobSubmitRequest,
    EvalMetricCatalog,
    EvalRunResult,
    EvalSyncRequest,
    EvalType,
    JobStatusDetail,
)
from cortex_contracts.openapi_examples import (
    EVAL_JOB_REQUEST_EXAMPLES,
    EVAL_SYNC_REQUEST_EXAMPLES,
    IDEMPOTENCY_KEY_EXAMPLE,
)
from cortex_db import CortexUnitOfWork
from cortex_domain import AccessLevel
from cortex_evaluation import EvaluationJobControlService, EvaluationService
from fastapi import APIRouter, Body, Depends, Header, Query, Request, Response, status

from ..dependencies.auth import get_current_caller
from ..dependencies.runtime import (
    get_auth_service,
    get_evaluation_job_service,
    get_evaluation_service,
    get_uow,
)
from ..services.jobs import get_job_status

router = APIRouter(prefix="/v1/eval", tags=["Evaluation"])


async def _authorize_eval_job(
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
        permission_key="eval:read",
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
    response_model=EvalEngineList,
    operation_id="listEvalEngines",
    summary="List evaluation engines",
    description=(
        "Returns the currently registered evaluation engines, supported evaluation types, "
        "execution modes, and default profile hints."
    ),
)
async def list_eval_engines(
    request: Request,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    evaluation_service: Annotated[EvaluationService, Depends(get_evaluation_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
) -> EvalEngineList:
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="eval:read",
        request_id=getattr(request.state, "request_id", None),
    )
    return evaluation_service.list_engines()


@router.get(
    "/metrics",
    response_model=EvalMetricCatalog,
    operation_id="listEvalMetrics",
    summary="List normalized evaluation metrics",
    description=(
        "Returns the normalized Cortex metric catalog that maps business-facing metric keys "
        "to engine-native implementations across DeepEval, EvalScope, and future adapters."
    ),
)
async def list_eval_metrics(
    request: Request,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    evaluation_service: Annotated[EvaluationService, Depends(get_evaluation_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
    evalType: Annotated[EvalType | None, Query()] = None,
    engineId: Annotated[str | None, Query()] = None,
) -> EvalMetricCatalog:
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="eval:read",
        request_id=getattr(request.state, "request_id", None),
    )
    return evaluation_service.list_metrics(eval_type=evalType, engine_id=engineId)


@router.post(
    "/sync",
    response_model=EvalRunResult,
    operation_id="runEvaluationSync",
    summary="Execute a synchronous evaluation run",
    description=(
        "Runs a small evaluation workload synchronously. Recommended for smoke checks, "
        "profile tuning, and low-cardinality datasets; larger workloads should use "
        "`/v1/eval/jobs`."
    ),
)
async def run_eval_sync(
    request: Request,
    payload: Annotated[
        EvalSyncRequest,
        Body(
            openapi_examples=EVAL_SYNC_REQUEST_EXAMPLES,
            description=(
                "Unified evaluation request body. Required: `eval_type` and `input`. "
                "`engine_id` defaults to `auto`."
            ),
        ),
    ],
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    evaluation_service: Annotated[EvaluationService, Depends(get_evaluation_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
) -> EvalRunResult:
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="eval:write",
        request_id=getattr(request.state, "request_id", None),
    )
    return await evaluation_service.run(payload)


@router.post(
    "/jobs",
    response_model=EvalJobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="createEvalJob",
    summary="Submit an asynchronous evaluation job",
    description=(
        "Queues a longer-running evaluation workload and returns a Cortex job handle for "
        "polling, events, and result retrieval."
    ),
)
async def create_eval_job(
    request: Request,
    payload: Annotated[
        EvalJobSubmitRequest,
        Body(
            openapi_examples=EVAL_JOB_REQUEST_EXAMPLES,
            description=(
                "Async evaluation job request. Use this for larger datasets, agent regressions, "
                "or scheduled validation workloads."
            ),
        ),
    ],
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    evaluation_service: Annotated[EvaluationService, Depends(get_evaluation_service)],
    evaluation_job_service: Annotated[
        EvaluationJobControlService, Depends(get_evaluation_job_service)
    ],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            description="Optional idempotency key for asynchronous evaluation job submission.",
            examples=[IDEMPOTENCY_KEY_EXAMPLE],
        ),
    ] = None,
) -> EvalJobAccepted:
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="eval:write",
        request_id=getattr(request.state, "request_id", None),
    )
    resolved = evaluation_service.resolve_request(payload)
    return await evaluation_job_service.submit(
        uow=uow,
        caller=caller,
        request=resolved.request,
        idempotency_key=idempotency_key,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "/jobs/{jobId}/result",
    response_model=EvalRunResult | JobStatusDetail,
    operation_id="getEvalResult",
    responses={409: {"model": JobStatusDetail}},
    summary="Get a completed evaluation result",
    description=(
        "Returns the completed evaluation result when the async job succeeds, or a 409 job "
        "status payload while work is still in progress."
    ),
)
async def get_eval_result(
    request: Request,
    response: Response,
    jobId: str,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    evaluation_job_service: Annotated[
        EvaluationJobControlService, Depends(get_evaluation_job_service)
    ],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
) -> EvalRunResult | JobStatusDetail:
    job = await _authorize_eval_job(
        request=request,
        job_id=jobId,
        caller=caller,
        auth_service=auth_service,
        uow=uow,
    )
    result = await evaluation_job_service.get_completed_result(uow=uow, job_id=jobId)
    if result is None:
        response.status_code = status.HTTP_409_CONFLICT
        return job
    return result
