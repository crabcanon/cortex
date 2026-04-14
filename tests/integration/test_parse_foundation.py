"""Integration tests for the Parse foundation package."""

import time
from pathlib import Path

import pytest
from cortex_auth import CallerContext
from cortex_common import CortexError
from cortex_contracts import (
    AccessLevel as ContractAccessLevel,
)
from cortex_contracts import (
    AccessPolicy,
    ChunkingOptions,
    ChunkingStrategy,
    ParseEngineDeploymentMode,
    ParseEngineDescriptor,
    ParseEngineStatus,
    ParseInputKind,
    ParseOutputOptions,
    ParsePersistenceOptions,
    ParserSelection,
    ParseSource,
    ParseSyncRequest,
)
from cortex_db import CortexUnitOfWork, create_database_engine, create_session_factory
from cortex_db.cli import main as db_migrate_main
from cortex_domain import ActorRecord, TenantRecord
from cortex_parse import (
    EngineExecutionContext,
    EngineExecutionResult,
    ParseEngineProtocol,
    ParseEngineRegistry,
    ParseProfileLoader,
    ParseService,
)


def _case_dir(name: str) -> Path:
    root = Path("runtime-test-data")
    root.mkdir(parents=True, exist_ok=True)
    case_dir = root / f"{name}-{time.time_ns()}"
    case_dir.mkdir(parents=True, exist_ok=True)
    return case_dir


def _sync_sqlite_url(db_path: Path) -> str:
    return f"sqlite:///{db_path.as_posix()}"


def _async_sqlite_url(db_path: Path) -> str:
    return f"sqlite+aiosqlite:///{db_path.as_posix()}"


class FailingEngine(ParseEngineProtocol):
    @property
    def descriptor(self) -> ParseEngineDescriptor:
        return ParseEngineDescriptor(
            engine_key="jina_reader",
            display_name="Jina Reader",
            engine_family="web_remote",
            deployment_mode=ParseEngineDeploymentMode.REMOTE,
            status=ParseEngineStatus.ACTIVE,
            supported_source_types=["url"],
            supported_formats=["text/html"],
            capabilities=["fast_extract"],
        )

    async def execute(self, context: EngineExecutionContext) -> EngineExecutionResult:
        raise CortexError(code="engine_unavailable", detail="upstream timeout", status_code=502)


class SuccessfulEngine(ParseEngineProtocol):
    @property
    def descriptor(self) -> ParseEngineDescriptor:
        return ParseEngineDescriptor(
            engine_key="crawl4ai",
            display_name="Crawl4AI",
            engine_family="web_interactive",
            deployment_mode=ParseEngineDeploymentMode.LOCAL,
            status=ParseEngineStatus.ACTIVE,
            supported_source_types=["url"],
            supported_formats=["text/html"],
            capabilities=["interactive_web", "anti_bot"],
        )

    async def execute(self, context: EngineExecutionContext) -> EngineExecutionResult:
        del context
        return EngineExecutionResult(
            markdown="# Example Doc\n\n\nParagraph one.\n\n## Details\n\nMore text.",
            source_format="text/html",
            detected_mime_type="text/html",
            metadata={
                "title": "Example Doc",
                "language": "en",
                "category_tags": ["docs"],
                "labels": ["guide"],
                "summary": "A short summary.",
            },
            raw_metadata={"site_name": "Example"},
            warnings=["normalized links"],
            link_counts={"internal": 3, "external": 1},
            media_counts={"images": 1, "videos": 0, "documents": 0},
            timings_ms={"fetch": 20, "render": 40},
            final_url="https://example.com/docs/final",
            http_status=200,
            content_length_bytes=2048,
            parser_version="1.0.0-test",
            engine_payload_summary={"strategy": "dom"},
        )


@pytest.mark.asyncio
async def test_parse_service_routes_fallback_normalizes_and_persists() -> None:
    case_dir = _case_dir("parse-foundation")
    db_path = case_dir / "cortex.db"
    profiles_dir = case_dir / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    (profiles_dir / "test_profile.yaml").write_text(
        "\n".join(
            [
                "profile_ref: test_profile",
                "display_name: Test Profile",
                "routing_mode: ordered_fallback",
                "preferred_engine_key: jina_reader",
                "allowed_engines: [jina_reader, crawl4ai]",
                "normalization_defaults:",
                "  schema_version: cortex.parse.v1",
                "fallback_policy:",
                "  enabled: true",
                "  mode: ordered",
                "  on_error: try_next",
                "  max_engine_attempts: 2",
            ]
        ),
        encoding="utf-8",
    )
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])

    engine = create_database_engine(_async_sqlite_url(db_path))
    session_factory = create_session_factory(engine)
    registry = ParseEngineRegistry()
    registry.register(FailingEngine())
    registry.register(SuccessfulEngine())
    service = ParseService(
        registry=registry,
        profile_loader=ParseProfileLoader(profiles_dir),
        default_profile_ref="test_profile",
    )
    caller = CallerContext(
        subject="alice",
        actor_id="alice",
        tenant_id="tenant_parse",
        actor_ref="alice@example.com",
        scopes=frozenset({"parse:write", "parse:read"}),
        roles=frozenset({"parse_operator"}),
    )

    try:
        async with CortexUnitOfWork(session_factory) as uow:
            await uow.tenants.add(
                TenantRecord(
                    tenant_id="tenant_parse",
                    tenant_key="tenant_parse",
                    display_name="Tenant Parse",
                    status="active",
                )
            )
            await uow.actors.add(
                ActorRecord(
                    actor_id="alice",
                    tenant_id="tenant_parse",
                    actor_type="user",
                    actor_ref="alice@example.com",
                    display_name="Alice",
                )
            )
            result = await service.parse(
                uow=uow,
                caller=caller,
                request=ParseSyncRequest(
                    source=ParseSource(
                        input_kind=ParseInputKind.URL,
                        url="https://example.com/docs",
                        expected_content_type="text/html",
                    ),
                    parser=ParserSelection(profile_ref="test_profile"),
                    output=ParseOutputOptions(
                        chunking=ChunkingOptions(
                            enabled=True,
                            strategy=ChunkingStrategy.HEADING,
                        )
                    ),
                    persistence=ParsePersistenceOptions(
                        access_policy=AccessPolicy(
                            access_level=ContractAccessLevel.RESTRICTED,
                            allowed_role_keys=["parse_operator"],
                        )
                    ),
                ),
            )

        assert result.job_id is not None
        assert result.document.title == "Example Doc"
        assert "\n\n\n" not in result.document.markdown
        assert result.document.parser.engine_key == "crawl4ai"
        assert result.diagnostics.selected_engine_key == "crawl4ai"
        assert len(result.diagnostics.engine_attempts) == 2
        assert result.diagnostics.engine_attempts[0].status.value == "failed"
        assert result.diagnostics.engine_attempts[1].status.value == "succeeded"
        assert result.document.access_policy == AccessPolicy(
            access_level=ContractAccessLevel.RESTRICTED,
            allowed_role_keys=["parse_operator"],
        )

        async with CortexUnitOfWork(session_factory) as uow:
            stored_job = await uow.jobs.get(result.job_id)
            stored_engine = await uow.parser_engines.get_by_key("crawl4ai")
            stored_profile = await uow.parser_profiles.get_by_key("tenant_parse", "test_profile")
            stored_document = await uow.documents.get(result.document.document_id)
            stored_tags = await uow.document_tags.list_for_document(result.document.document_id)
            stored_chunks = await uow.document_chunks.list_for_document(result.document.document_id)
            stored_run = await uow.parse_runs.get_by_job(result.job_id)
            assert stored_run is not None
            stored_attempts = await uow.parse_run_attempts.list_for_run(stored_run.parse_run_id)

        assert stored_job is not None
        assert stored_job.status is not None and stored_job.status.value == "succeeded"
        assert stored_engine is not None
        assert stored_profile is not None
        assert stored_document is not None
        assert stored_document.language_code == "en"
        assert len(stored_tags) == 2
        assert {tag.tag for tag in stored_tags} == {"docs", "guide"}
        assert len(stored_chunks) == 2
        assert stored_chunks[0].heading_path == "Example Doc"
        assert stored_run is not None
        assert stored_run.selected_engine_id == stored_engine.engine_id
        assert len(stored_attempts) == 2
        assert stored_attempts[0].error_code == "engine_unavailable"
        assert stored_attempts[1].engine_result["strategy"] == "dom"
    finally:
        await engine.dispose()
