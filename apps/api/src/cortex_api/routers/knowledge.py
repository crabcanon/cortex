"""Knowledge dataset, job submission, and search endpoints."""

from typing import Annotated

from cortex_auth import (
    AuthorizationDeniedError,
    AuthorizationService,
    CallerContext,
)
from cortex_contracts import (
    AddJobRequest,
    CognifyJobRequest,
    JobAccepted,
    KnowledgeDataset,
    KnowledgeDatasetCreateRequest,
    MemifyJobRequest,
    SearchRequest,
    SearchResponse,
)
from cortex_db import CortexUnitOfWork
from cortex_domain import DatasetRecord
from cortex_knowledge import (
    KnowledgeDatasetService,
    KnowledgeJobControlService,
    KnowledgeSearchService,
)
from fastapi import APIRouter, Depends, Header, Request, status

from ..dependencies.auth import get_current_caller
from ..dependencies.runtime import (
    get_auth_service,
    get_knowledge_job_service,
    get_knowledge_search_service,
    get_knowledge_service,
    get_uow,
)
from ..services.knowledge import build_resource_context, get_dataset_record

router = APIRouter(prefix="/v1/knowledge", tags=["Knowledge"])
KnowledgeJobServiceDep = Annotated[
    KnowledgeJobControlService,
    Depends(get_knowledge_job_service),
]
KnowledgeSearchServiceDep = Annotated[
    KnowledgeSearchService,
    Depends(get_knowledge_search_service),
]


async def _authorize_dataset(
    *,
    request: Request,
    caller: CallerContext,
    auth_service: AuthorizationService,
    knowledge_service: KnowledgeDatasetService,
    uow: CortexUnitOfWork,
    dataset: DatasetRecord,
    permission_key: str,
) -> None:
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key=permission_key,
        request_id=getattr(request.state, "request_id", None),
        resource=build_resource_context(knowledge_service, dataset),
    )


async def _resolve_dataset_ref(
    *,
    knowledge_service: KnowledgeDatasetService,
    uow: CortexUnitOfWork,
    tenant_id: str,
    dataset_id: str | None,
    dataset_key: str | None,
) -> DatasetRecord:
    return await knowledge_service.resolve_dataset(
        uow=uow,
        tenant_id=tenant_id,
        dataset_id=dataset_id,
        dataset_key=dataset_key,
    )


async def _authorized_search_scope(
    *,
    request: Request,
    caller: CallerContext,
    auth_service: AuthorizationService,
    knowledge_service: KnowledgeDatasetService,
    uow: CortexUnitOfWork,
    search_request: SearchRequest,
) -> list[DatasetRecord]:
    if search_request.dataset_ids or search_request.dataset_keys:
        datasets: list[DatasetRecord] = []
        for dataset_id in list(dict.fromkeys(search_request.dataset_ids)):
            datasets.append(
                await _resolve_dataset_ref(
                    knowledge_service=knowledge_service,
                    uow=uow,
                    tenant_id=caller.tenant_id,
                    dataset_id=dataset_id,
                    dataset_key=None,
                )
            )
        for dataset_key in list(dict.fromkeys(search_request.dataset_keys)):
            datasets.append(
                await _resolve_dataset_ref(
                    knowledge_service=knowledge_service,
                    uow=uow,
                    tenant_id=caller.tenant_id,
                    dataset_id=None,
                    dataset_key=dataset_key,
                )
            )
        unique: dict[str, DatasetRecord] = {dataset.dataset_id: dataset for dataset in datasets}
        for dataset in unique.values():
            await _authorize_dataset(
                request=request,
                caller=caller,
                auth_service=auth_service,
                knowledge_service=knowledge_service,
                uow=uow,
                dataset=dataset,
                permission_key="knowledge:read",
            )
        return list(unique.values())

    datasets = list(await uow.datasets.list_for_tenant(caller.tenant_id))
    allowed: list[DatasetRecord] = []
    for dataset in datasets:
        try:
            await _authorize_dataset(
                request=request,
                caller=caller,
                auth_service=auth_service,
                knowledge_service=knowledge_service,
                uow=uow,
                dataset=dataset,
                permission_key="knowledge:read",
            )
        except AuthorizationDeniedError:
            continue
        allowed.append(dataset)
    return allowed


@router.post(
    "/datasets",
    response_model=KnowledgeDataset,
    status_code=status.HTTP_201_CREATED,
    operation_id="createKnowledgeDataset",
    summary="Create a knowledge dataset",
)
async def create_knowledge_dataset(
    request: Request,
    payload: KnowledgeDatasetCreateRequest,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    knowledge_service: Annotated[KnowledgeDatasetService, Depends(get_knowledge_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> KnowledgeDataset:
    del idempotency_key
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="knowledge:write",
        request_id=getattr(request.state, "request_id", None),
    )
    return await knowledge_service.create_dataset(uow=uow, caller=caller, request=payload)


@router.get(
    "/datasets/{datasetId}",
    response_model=KnowledgeDataset,
    operation_id="getKnowledgeDataset",
    summary="Get dataset metadata and counters",
)
async def get_knowledge_dataset(
    request: Request,
    datasetId: str,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    knowledge_service: Annotated[KnowledgeDatasetService, Depends(get_knowledge_service)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
) -> KnowledgeDataset:
    record = await get_dataset_record(knowledge_service, uow, datasetId)
    await _authorize_dataset(
        request=request,
        caller=caller,
        auth_service=auth_service,
        knowledge_service=knowledge_service,
        uow=uow,
        dataset=record,
        permission_key="knowledge:read",
    )
    return await knowledge_service.get_dataset(uow=uow, dataset_id=datasetId)


@router.post(
    "/add/jobs",
    response_model=JobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="createAddJob",
    summary="Submit a Cognee Add job",
)
async def create_add_job(
    request: Request,
    payload: AddJobRequest,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    knowledge_service: Annotated[KnowledgeDatasetService, Depends(get_knowledge_service)],
    knowledge_job_service: KnowledgeJobServiceDep,
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> JobAccepted:
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="knowledge:write",
        request_id=getattr(request.state, "request_id", None),
    )
    dataset = await _resolve_dataset_ref(
        knowledge_service=knowledge_service,
        uow=uow,
        tenant_id=caller.tenant_id,
        dataset_id=payload.dataset_id,
        dataset_key=payload.dataset_key,
    )
    await _authorize_dataset(
        request=request,
        caller=caller,
        auth_service=auth_service,
        knowledge_service=knowledge_service,
        uow=uow,
        dataset=dataset,
        permission_key="knowledge:write",
    )
    return await knowledge_job_service.submit_add(
        uow=uow,
        caller=caller,
        dataset=dataset,
        request=payload,
        idempotency_key=idempotency_key,
        request_id=getattr(request.state, "request_id", None),
    )


@router.post(
    "/cognify/jobs",
    response_model=JobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="createCognifyJob",
    summary="Submit a Cognify job",
)
async def create_cognify_job(
    request: Request,
    payload: CognifyJobRequest,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    knowledge_service: Annotated[KnowledgeDatasetService, Depends(get_knowledge_service)],
    knowledge_job_service: KnowledgeJobServiceDep,
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> JobAccepted:
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="knowledge:write",
        request_id=getattr(request.state, "request_id", None),
    )
    dataset = await _resolve_dataset_ref(
        knowledge_service=knowledge_service,
        uow=uow,
        tenant_id=caller.tenant_id,
        dataset_id=payload.dataset_id,
        dataset_key=payload.dataset_key,
    )
    await _authorize_dataset(
        request=request,
        caller=caller,
        auth_service=auth_service,
        knowledge_service=knowledge_service,
        uow=uow,
        dataset=dataset,
        permission_key="knowledge:write",
    )
    return await knowledge_job_service.submit_cognify(
        uow=uow,
        caller=caller,
        dataset=dataset,
        request=payload,
        idempotency_key=idempotency_key,
        request_id=getattr(request.state, "request_id", None),
    )


@router.post(
    "/memify/jobs",
    response_model=JobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="createMemifyJob",
    summary="Submit a Memify job",
)
async def create_memify_job(
    request: Request,
    payload: MemifyJobRequest,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    knowledge_service: Annotated[KnowledgeDatasetService, Depends(get_knowledge_service)],
    knowledge_job_service: KnowledgeJobServiceDep,
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> JobAccepted:
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="knowledge:write",
        request_id=getattr(request.state, "request_id", None),
    )
    dataset = await _resolve_dataset_ref(
        knowledge_service=knowledge_service,
        uow=uow,
        tenant_id=caller.tenant_id,
        dataset_id=payload.dataset_id,
        dataset_key=payload.dataset_key,
    )
    await _authorize_dataset(
        request=request,
        caller=caller,
        auth_service=auth_service,
        knowledge_service=knowledge_service,
        uow=uow,
        dataset=dataset,
        permission_key="knowledge:write",
    )
    return await knowledge_job_service.submit_memify(
        uow=uow,
        caller=caller,
        dataset=dataset,
        request=payload,
        idempotency_key=idempotency_key,
        request_id=getattr(request.state, "request_id", None),
    )


@router.post(
    "/search",
    response_model=SearchResponse,
    operation_id="searchKnowledge",
    summary="Search across datasets and knowledge graphs",
)
async def search_knowledge(
    request: Request,
    payload: SearchRequest,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    knowledge_service: Annotated[KnowledgeDatasetService, Depends(get_knowledge_service)],
    knowledge_search_service: KnowledgeSearchServiceDep,
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
) -> SearchResponse:
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="knowledge:read",
        request_id=getattr(request.state, "request_id", None),
    )
    datasets = await _authorized_search_scope(
        request=request,
        caller=caller,
        auth_service=auth_service,
        knowledge_service=knowledge_service,
        uow=uow,
        search_request=payload,
    )
    return await knowledge_search_service.search(
        uow=uow,
        caller=caller,
        request=payload,
        datasets=datasets,
    )
