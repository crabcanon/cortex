"""Shared evaluation adapter primitives."""

from __future__ import annotations

from cortex_common import CortexError
from cortex_contracts import EvalEngineDescriptor, EvalRunResult, EvalSyncRequest


class DisabledEvaluationEngine:
    """Engine placeholder used when a runtime is intentionally disabled."""

    def __init__(self, descriptor: EvalEngineDescriptor, reason: str) -> None:
        self._descriptor = descriptor.model_copy(update={"notes": reason})

    @property
    def descriptor(self) -> EvalEngineDescriptor:
        return self._descriptor

    async def run(self, request: EvalSyncRequest) -> EvalRunResult:
        del request
        raise CortexError(
            code="eval_engine_unavailable",
            detail=f"Evaluation engine `{self.descriptor.engine_id}` is not available.",
            status_code=503,
        )
