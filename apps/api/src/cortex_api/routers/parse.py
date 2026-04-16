"""Parse engine catalog and synchronous parse endpoints."""

from typing import Annotated

from cortex_auth import AuthorizationService, CallerContext, ResourceAuthorizationContext
from cortex_contracts import (
    JobAccepted,
    JobStatusDetail,
    ParseBatchJobAccepted,
    ParseBatchResult,
    ParseEngineList,
    ParseJobSubmitRequest,
    ParseResult,
    ParserProfileList,
    ParseSubmitRequest,
)
from cortex_contracts.openapi_examples import (
    IDEMPOTENCY_KEY_EXAMPLE,
    JOB_ID_EXAMPLE,
    PARSE_JOB_REQUEST_EXAMPLES,
    PARSE_SYNC_REQUEST_EXAMPLES,
)
from cortex_db import CortexUnitOfWork
from cortex_domain import AccessLevel
from cortex_parse import ParseJobControlService, ParseRequestCompiler, ParseService
from cortex_storage import StorageService
from fastapi import APIRouter, Body, Depends, Header, Path, Request, Response, status

from ..dependencies.auth import get_current_caller
from ..dependencies.runtime import (
    get_auth_service,
    get_parse_job_service,
    get_parse_request_compiler,
    get_parse_service,
    get_storage_service,
    get_uow,
)
from ..services.jobs import get_job_status
from ..services.parse_requests import compile_parse_job_requests, compile_parse_sync_requests

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
    operation_id="listParseEngines",
    summary="List available parse engines",
    description=(
        "Return the registered parser engines, supported source kinds, default scene, supported "
        "scenes, and the default internal profile that the Parse request compiler will bind for "
        "each engine."
    ),
)
async def list_parse_engines(
    request: Request,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    parse_service: Annotated[ParseService, Depends(get_parse_service)],
    parse_request_compiler: Annotated[
        ParseRequestCompiler, Depends(get_parse_request_compiler)
    ],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
) -> ParseEngineList:
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="parse:read",
        request_id=getattr(request.state, "request_id", None),
    )
    return parse_request_compiler.describe_engines(parse_service.list_engines())


@router.get(
    "/profiles",
    response_model=ParserProfileList,
    operation_id="listParserProfiles",
    summary="List parser profiles",
    description=(
        "Return the internal parser profiles available to operators and debugging workflows. "
        "Most API callers should not need them because the public Parse API compiles "
        "`source + engine_id (+ scene)` into these profiles automatically."
    ),
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
    response_model=ParseBatchResult,
    operation_id="parseContentSync",
    summary="Parse content synchronously",
    description=(
        "Synchronously parse one or more source locators into LLM-ready Markdown. "
        "The public contract is centered on `sources`, `engine_id`, and optional `scene`."
    ),
)
async def parse_content_sync(
    request: Request,
    payload: Annotated[
        ParseSubmitRequest,
        Body(
            openapi_examples=PARSE_SYNC_REQUEST_EXAMPLES,
            description=(
                "Unified Parse request body. Required: `sources`. `engine_id` defaults to `auto`, "
                "and `scene` is optional."
            ),
        ),
    ],
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    parse_service: Annotated[ParseService, Depends(get_parse_service)],
    parse_request_compiler: Annotated[
        ParseRequestCompiler, Depends(get_parse_request_compiler)
    ],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            description=(
                "Optional idempotency key for safely retrying synchronous parse submissions. "
                "Best default: omit unless the caller may retry the same request."
            ),
            examples=[IDEMPOTENCY_KEY_EXAMPLE],
        ),
    ] = None,
) -> ParseBatchResult:
    del idempotency_key
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="parse:write",
        request_id=getattr(request.state, "request_id", None),
    )
    compiled_requests = await compile_parse_sync_requests(
        payload=payload,
        caller=caller,
        auth_service=auth_service,
        storage_service=storage_service,
        compiler=parse_request_compiler,
        uow=uow,
        request_id=getattr(request.state, "request_id", None),
    )
    results = [
        await parse_service.parse(uow=uow, caller=caller, request=compiled_request)
        for compiled_request in compiled_requests
    ]
    return ParseBatchResult(
        requested_sources=list(payload.sources),
        engine_id=payload.engine_id,
        scene=payload.scene,
        results=results,
    )


@router.post(
    "/jobs",
    response_model=ParseBatchJobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="createParseJob",
    summary="Submit an asynchronous parse job",
    description=(
        "Queue one async parse job per source using the same unified public Parse contract. "
        "Add optional `priority` and `webhook` only when job control is needed."
    ),
)
async def create_parse_job(
    request: Request,
    payload: Annotated[
        ParseJobSubmitRequest,
        Body(
            openapi_examples=PARSE_JOB_REQUEST_EXAMPLES,
            description=(
                "Unified async Parse request. `sources` may contain one or more locators; "
                "`engine_id` defaults to `auto`."
            ),
        ),
    ],
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    parse_job_service: Annotated[ParseJobControlService, Depends(get_parse_job_service)],
    parse_request_compiler: Annotated[
        ParseRequestCompiler, Depends(get_parse_request_compiler)
    ],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            description=(
                "Optional idempotency key for safely retrying asynchronous job submission. "
                "Best default: omit unless a client may re-send the same create request."
            ),
            examples=[IDEMPOTENCY_KEY_EXAMPLE],
        ),
    ] = None,
) -> ParseBatchJobAccepted:
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="parse:write",
        request_id=getattr(request.state, "request_id", None),
    )
    compiled_requests = await compile_parse_job_requests(
        payload=payload,
        caller=caller,
        auth_service=auth_service,
        storage_service=storage_service,
        compiler=parse_request_compiler,
        uow=uow,
        request_id=getattr(request.state, "request_id", None),
    )
    jobs: list[JobAccepted] = []
    for index, compiled_request in enumerate(compiled_requests):
        batch_key = (
            f"{idempotency_key}:{index}"
            if idempotency_key is not None and len(compiled_requests) > 1
            else idempotency_key
        )
        jobs.append(
            await parse_job_service.submit(
                uow=uow,
                caller=caller,
                request=compiled_request,
                idempotency_key=batch_key,
                request_id=getattr(request.state, "request_id", None),
            )
        )
    return ParseBatchJobAccepted(
        requested_sources=list(payload.sources),
        engine_id=payload.engine_id,
        scene=payload.scene,
        jobs=jobs,
    )


@router.get(
    "/jobs/{jobId}/result",
    response_model=ParseResult | JobStatusDetail,
    operation_id="getParseResult",
    summary="Get a completed parse result",
    responses={202: {"model": JobStatusDetail}},
    description=(
        "Poll for the parse result. Returns `202` with job status until the parse completes, "
        "then returns the final `ParseResult`."
    ),
)
async def get_parse_job_result(
    request: Request,
    response: Response,
    jobId: Annotated[
        str,
        Path(
            description="Parse job identifier returned by `/v1/parse/jobs`.",
            examples=[JOB_ID_EXAMPLE],
        ),
    ],
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    parse_job_service: Annotated[ParseJobControlService, Depends(get_parse_job_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
) -> ParseResult | JobStatusDetail:
    job = await _authorize_parse_job(
        request=request,
        job_id=jobId,
        caller=caller,
        auth_service=auth_service,
        uow=uow,
    )
    result = await parse_job_service.get_completed_result(uow=uow, job_id=jobId)
    if result is None:
        response.status_code = status.HTTP_202_ACCEPTED
        return job
    return result
