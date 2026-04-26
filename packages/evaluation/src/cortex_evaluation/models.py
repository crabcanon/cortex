"""Evaluation engine protocols and runtime helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from cortex_contracts import EvalEngineDescriptor, EvalRunResult, EvalSyncRequest

EvalRequestT = TypeVar("EvalRequestT", bound=EvalSyncRequest)


@dataclass(slots=True)
class ResolvedEvalRequest(Generic[EvalRequestT]):
    request: EvalRequestT
    engine_id: str


class EvaluationEngineProtocol(Protocol):
    @property
    def descriptor(self) -> EvalEngineDescriptor: ...

    async def run(self, request: EvalSyncRequest) -> EvalRunResult: ...
