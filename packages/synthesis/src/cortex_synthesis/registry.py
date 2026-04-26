"""Synthesis engine registry."""

from __future__ import annotations

from collections.abc import Iterable

from .models import SynthesisEngineProtocol


class SynthesisEngineRegistry:
    def __init__(self) -> None:
        self._engines: dict[str, SynthesisEngineProtocol] = {}

    def register(self, engine: SynthesisEngineProtocol) -> None:
        self._engines[engine.descriptor.engine_id] = engine

    def get(self, engine_id: str) -> SynthesisEngineProtocol | None:
        return self._engines.get(engine_id)

    def list_all(self) -> tuple[SynthesisEngineProtocol, ...]:
        return tuple(self._engines.values())

    def list_available(self) -> tuple[SynthesisEngineProtocol, ...]:
        return tuple(
            engine
            for engine in self._engines.values()
            if engine.descriptor.availability_status in {"available", "degraded"}
        )

    def __iter__(self) -> Iterable[SynthesisEngineProtocol]:
        return iter(self._engines.values())
