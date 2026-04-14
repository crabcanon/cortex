"""Optional Cognee runtime adapter."""

from __future__ import annotations

import asyncio
import importlib
import importlib.metadata
from collections.abc import Awaitable, Callable
from typing import Any, cast

from cortex_common import CogneeSettings, ConfigError

from .models import CogneeRuntimeDescriptor, CogneeRuntimeProtocol


def _load_cognee_module() -> Any:
    try:
        return importlib.import_module("cognee")
    except ImportError as exc:  # pragma: no cover - depends on optional dependency
        raise ConfigError(
            "Cognee runtime is not installed. Install `cognee` to enable knowledge operations."
        ) from exc


def _cognee_available() -> bool:
    try:
        _load_cognee_module()
    except Exception:
        return False
    return True


def _cognee_version() -> str | None:
    try:
        return importlib.metadata.version("cognee")
    except importlib.metadata.PackageNotFoundError:  # pragma: no cover - optional dependency
        return None


class DisabledCogneeRuntime(CogneeRuntimeProtocol):
    def __init__(self, *, reason: str) -> None:
        self._descriptor = CogneeRuntimeDescriptor(
            provider_key="cognee",
            display_name="Cognee",
            status="disabled",
            capabilities=[],
            version=_cognee_version(),
            reason=reason,
        )

    @property
    def descriptor(self) -> CogneeRuntimeDescriptor:
        return self._descriptor

    async def add(self, *, dataset: str, payload: dict[str, Any]) -> dict[str, Any]:
        del dataset, payload
        raise ConfigError(self._descriptor.reason or "Cognee runtime is disabled.")

    async def cognify(self, *, dataset: str, payload: dict[str, Any]) -> dict[str, Any]:
        del dataset, payload
        raise ConfigError(self._descriptor.reason or "Cognee runtime is disabled.")

    async def memify(self, *, dataset: str, payload: dict[str, Any]) -> dict[str, Any]:
        del dataset, payload
        raise ConfigError(self._descriptor.reason or "Cognee runtime is disabled.")

    async def search(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        del payload
        raise ConfigError(self._descriptor.reason or "Cognee runtime is disabled.")


class PythonCogneeRuntime(CogneeRuntimeProtocol):
    def __init__(self) -> None:
        available = _cognee_available()
        self._descriptor = CogneeRuntimeDescriptor(
            provider_key="cognee",
            display_name="Cognee",
            status="active" if available else "disabled",
            capabilities=["add", "cognify", "memify", "search"] if available else [],
            version=_cognee_version(),
            reason=None if available else "Cognee runtime module is unavailable.",
        )
        self._module = _load_cognee_module() if available else None

    @property
    def descriptor(self) -> CogneeRuntimeDescriptor:
        return self._descriptor

    async def add(self, *, dataset: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._invoke("add", dataset=dataset, **payload)

    async def cognify(self, *, dataset: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._invoke("cognify", dataset=dataset, **payload)

    async def memify(self, *, dataset: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._invoke("memify", dataset=dataset, **payload)

    async def search(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._invoke("search", **payload)

    async def _invoke(self, method_name: str, **kwargs: Any) -> dict[str, Any]:
        if self._module is None:
            raise ConfigError("Cognee runtime module is unavailable.")
        target = getattr(self._module, method_name, None)
        if target is None:
            raise ConfigError(f"Cognee runtime does not expose `{method_name}`.")
        if asyncio.iscoroutinefunction(target):
            result = await cast(Callable[..., Awaitable[Any]], target)(**kwargs)
        else:
            result = await asyncio.to_thread(cast(Callable[..., Any], target), **kwargs)
        if isinstance(result, dict):
            return result
        return {"result": result}


def build_cognee_runtime(settings: CogneeSettings) -> CogneeRuntimeProtocol:
    if not settings.enabled:
        return DisabledCogneeRuntime(reason="Cognee runtime is disabled by configuration.")
    runtime = PythonCogneeRuntime()
    if runtime.descriptor.status != "active":
        return DisabledCogneeRuntime(
            reason=runtime.descriptor.reason or "Cognee runtime module is unavailable."
        )
    return runtime
