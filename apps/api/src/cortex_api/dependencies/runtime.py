"""Runtime dependency helpers."""

from collections.abc import AsyncIterator

from cortex_auth import AuthorizationService
from cortex_common import CortexSettings
from cortex_db import CortexUnitOfWork, SessionFactory
from cortex_evaluation import EvaluationJobControlService, EvaluationService
from cortex_knowledge import (
    KnowledgeDatasetService,
    KnowledgeJobControlService,
    KnowledgeSearchService,
)
from cortex_parse import ParseJobControlService, ParseRequestCompiler, ParseService
from cortex_storage import StorageService
from cortex_synthesis import SynthesisJobControlService, SynthesisService
from fastapi import Request


def get_settings(request: Request) -> CortexSettings:
    return request.app.state.settings  # type: ignore[no-any-return]


def get_session_factory(request: Request) -> SessionFactory:
    return request.app.state.session_factory  # type: ignore[no-any-return]


def get_auth_service(request: Request) -> AuthorizationService:
    return request.app.state.auth_service  # type: ignore[no-any-return]


def get_storage_service(request: Request) -> StorageService:
    return request.app.state.storage_service  # type: ignore[no-any-return]


def get_evaluation_service(request: Request) -> EvaluationService:
    return request.app.state.evaluation_service  # type: ignore[no-any-return]


def get_evaluation_job_service(request: Request) -> EvaluationJobControlService:
    return request.app.state.evaluation_job_service  # type: ignore[no-any-return]


def get_knowledge_service(request: Request) -> KnowledgeDatasetService:
    return request.app.state.knowledge_service  # type: ignore[no-any-return]


def get_knowledge_job_service(request: Request) -> KnowledgeJobControlService:
    return request.app.state.knowledge_job_service  # type: ignore[no-any-return]


def get_knowledge_search_service(request: Request) -> KnowledgeSearchService:
    return request.app.state.knowledge_search_service  # type: ignore[no-any-return]


def get_parse_service(request: Request) -> ParseService:
    return request.app.state.parse_service  # type: ignore[no-any-return]


def get_parse_request_compiler(request: Request) -> ParseRequestCompiler:
    return request.app.state.parse_request_compiler  # type: ignore[no-any-return]


def get_parse_job_service(request: Request) -> ParseJobControlService:
    return request.app.state.parse_job_service  # type: ignore[no-any-return]


def get_synthesis_service(request: Request) -> SynthesisService:
    return request.app.state.synthesis_service  # type: ignore[no-any-return]


def get_synthesis_job_service(request: Request) -> SynthesisJobControlService:
    return request.app.state.synthesis_job_service  # type: ignore[no-any-return]


async def get_uow(request: Request) -> AsyncIterator[CortexUnitOfWork]:
    session_factory = get_session_factory(request)
    async with CortexUnitOfWork(session_factory) as uow:
        yield uow
