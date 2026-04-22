"""Application lifespan hooks."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from cortex_auth import AuthorizationService
from cortex_common import load_runtime_config, load_settings
from cortex_db import create_database_engine, create_session_factory
from cortex_knowledge import (
    KnowledgeDatasetService,
    KnowledgeJobControlService,
    KnowledgeSearchService,
    build_cognee_runtime,
)
from cortex_observability import configure_telemetry, install_logging_correlation
from cortex_parse import (
    ParseJobControlService,
    ParseRequestCompiler,
    build_parse_service,
    prepare_crawl4ai_playwright_runtime,
)
from cortex_storage import StorageService
from fastapi import FastAPI


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _probe_override_from_env() -> bool | None:
    raw = os.getenv("CORTEX_CRAWL4AI_SKIP_PROBE")
    if raw is None or not raw.strip():
        return None
    return not _env_flag("CORTEX_CRAWL4AI_SKIP_PROBE")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Bootstrap runtime settings, telemetry, persistence, and auth services."""
    settings = load_settings()
    runtime_config = load_runtime_config(settings.runtime.path)
    prepare_crawl4ai_playwright_runtime(
        runtime_config,
        install_if_missing=_env_flag("CORTEX_CRAWL4AI_INSTALL_IF_MISSING"),
        with_deps=_env_flag("CORTEX_CRAWL4AI_WITH_DEPS"),
        probe=_probe_override_from_env(),
    )
    telemetry = configure_telemetry("cortex-api", settings.telemetry)
    engine = create_database_engine(settings.database.dsn)
    session_factory = create_session_factory(engine)
    auth_service = AuthorizationService(settings.auth)
    storage_service = StorageService(settings.s3)
    knowledge_runtime = build_cognee_runtime(settings.cognee, runtime_config)
    knowledge_service = KnowledgeDatasetService(knowledge_runtime)
    knowledge_job_service = KnowledgeJobControlService()
    knowledge_search_service = KnowledgeSearchService(knowledge_runtime)
    parse_service = build_parse_service(settings.parse, runtime_config)
    parse_request_compiler = ParseRequestCompiler(
        {descriptor.engine_key for descriptor in parse_service.list_engines().engines}
    )
    parse_job_service = ParseJobControlService()
    logger = install_logging_correlation()

    app.state.settings = settings
    app.state.runtime_config = runtime_config
    app.state.telemetry = telemetry
    app.state.db_engine = engine
    app.state.session_factory = session_factory
    app.state.auth_service = auth_service
    app.state.storage_service = storage_service
    app.state.knowledge_service = knowledge_service
    app.state.knowledge_job_service = knowledge_job_service
    app.state.knowledge_search_service = knowledge_search_service
    app.state.parse_service = parse_service
    app.state.parse_request_compiler = parse_request_compiler
    app.state.parse_job_service = parse_job_service
    app.state.logger = logger

    try:
        yield
    finally:
        await engine.dispose()
