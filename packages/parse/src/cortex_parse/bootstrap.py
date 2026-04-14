"""Runtime bootstrap helpers for parse orchestration."""

from __future__ import annotations

from cortex_common import ParseSettings
from cortex_contracts import ParseEngineStatus

from .adapters import (
    Crawl4AIParseEngine,
    DoclingParseEngine,
    JinaReaderParseEngine,
    MarkItDownParseEngine,
)
from .profile_loader import ParseProfileLoader
from .registry import ParseEngineRegistry
from .service import ParseService


def build_parse_service(settings: ParseSettings) -> ParseService:
    """Build the default parse runtime for the API process."""
    registry = ParseEngineRegistry()
    for engine in (
        Crawl4AIParseEngine(),
        JinaReaderParseEngine(),
        MarkItDownParseEngine(),
        DoclingParseEngine(),
    ):
        if engine.descriptor.status is ParseEngineStatus.ACTIVE:
            registry.register(engine)

    return ParseService(
        registry=registry,
        profile_loader=ParseProfileLoader(),
        default_profile_ref=settings.default_profile,
    )
