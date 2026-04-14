"""Parse engine registry."""

from __future__ import annotations

from cortex_contracts import ParseEngineDescriptor, ParseEngineList, ParseEngineStatus

from .models import ParseEngineProtocol, engine_list


class ParseEngineRegistry:
    """In-memory registry of available parse engines."""

    def __init__(self) -> None:
        self._engines: dict[str, ParseEngineProtocol] = {}

    def register(self, engine: ParseEngineProtocol) -> None:
        self._engines[engine.descriptor.engine_key] = engine

    def get(self, engine_key: str) -> ParseEngineProtocol | None:
        return self._engines.get(engine_key)

    def descriptors(self, *, include_inactive: bool = False) -> list[ParseEngineDescriptor]:
        descriptors = [engine.descriptor for engine in self._engines.values()]
        if include_inactive:
            return descriptors
        return [
            descriptor
            for descriptor in descriptors
            if descriptor.status is ParseEngineStatus.ACTIVE
        ]

    def list(self, *, include_inactive: bool = False) -> ParseEngineList:
        return engine_list(self.descriptors(include_inactive=include_inactive))
