"""Shared exception hierarchy."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CortexError(Exception):
    """Base exception carrying stable error metadata."""

    code: str
    detail: str
    status_code: int = 400
    extra: Mapping[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


class ConfigError(CortexError):
    """Raised when runtime configuration is invalid."""

    def __init__(self, detail: str, *, extra: Mapping[str, Any] | None = None) -> None:
        super().__init__("config_error", detail, 500, extra or {})


class ValidationError(CortexError):
    """Raised when caller input fails business validation."""

    def __init__(self, detail: str, *, extra: Mapping[str, Any] | None = None) -> None:
        super().__init__("validation_error", detail, 422, extra or {})


class NotFoundError(CortexError):
    """Raised when a requested resource does not exist."""

    def __init__(self, detail: str, *, extra: Mapping[str, Any] | None = None) -> None:
        super().__init__("not_found", detail, 404, extra or {})
