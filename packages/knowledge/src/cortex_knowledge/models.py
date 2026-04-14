"""Knowledge runtime abstractions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class CogneeRuntimeDescriptor:
    provider_key: str
    display_name: str
    status: str
    capabilities: list[str] = field(default_factory=list)
    version: str | None = None
    reason: str | None = None


class CogneeRuntimeProtocol(Protocol):
    @property
    def descriptor(self) -> CogneeRuntimeDescriptor: ...

    async def add(self, *, dataset: str, payload: dict[str, Any]) -> dict[str, Any]: ...

    async def cognify(self, *, dataset: str, payload: dict[str, Any]) -> dict[str, Any]: ...

    async def memify(self, *, dataset: str, payload: dict[str, Any]) -> dict[str, Any]: ...

    async def search(self, *, payload: dict[str, Any]) -> dict[str, Any]: ...
