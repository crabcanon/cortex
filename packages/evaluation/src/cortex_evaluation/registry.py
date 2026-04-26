"""Evaluation engine registry."""

from __future__ import annotations

from collections.abc import Iterable

from .models import EvaluationEngineProtocol


class EvaluationEngineRegistry:
    def __init__(self) -> None:
        self._engines: dict[str, EvaluationEngineProtocol] = {}

    def register(self, engine: EvaluationEngineProtocol) -> None:
        self._engines[engine.descriptor.engine_id] = engine

    def get(self, engine_id: str) -> EvaluationEngineProtocol | None:
        return self._engines.get(engine_id)

    def list_all(self) -> tuple[EvaluationEngineProtocol, ...]:
        return tuple(self._engines.values())

    def list_available(self) -> tuple[EvaluationEngineProtocol, ...]:
        return tuple(
            engine
            for engine in self._engines.values()
            if engine.descriptor.availability_status in {"available", "degraded"}
        )

    def __iter__(self) -> Iterable[EvaluationEngineProtocol]:
        return iter(self._engines.values())
