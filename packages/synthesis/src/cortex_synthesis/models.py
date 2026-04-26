"""Synthesis engine protocols and runtime helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from cortex_contracts import (
    SynthesisEngineDescriptor,
    SynthesisRunResult,
    SynthesisSyncRequest,
)

SynthesisRequestT = TypeVar("SynthesisRequestT", bound=SynthesisSyncRequest)


@dataclass(slots=True)
class ResolvedSynthesisRequest(Generic[SynthesisRequestT]):
    request: SynthesisRequestT
    engine_id: str


class SynthesisEngineProtocol(Protocol):
    @property
    def descriptor(self) -> SynthesisEngineDescriptor: ...

    async def run(self, request: SynthesisSyncRequest) -> SynthesisRunResult: ...
