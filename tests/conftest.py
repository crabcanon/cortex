"""Shared pytest configuration for workspace-wide test hygiene."""

from __future__ import annotations

import warnings

try:  # pragma: no cover - depends on installed pydantic version
    from pydantic.warnings import PydanticDeprecatedSince20
except Exception:  # pragma: no cover - fallback for older/newer pydantic
    PydanticDeprecatedSince20 = DeprecationWarning


def pytest_configure() -> None:
    """Hide known upstream Cognee deprecations until the dependency updates."""
    warnings.filterwarnings(
        "ignore",
        message=(
            r"'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated\. "
            r"Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead\."
        ),
        category=DeprecationWarning,
        module=r"cognee\.exceptions\.exceptions",
    )
    warnings.filterwarnings(
        "ignore",
        message=r"Using extra keyword arguments on `Field` is deprecated and will be removed\..*",
        category=PydanticDeprecatedSince20,
        module=r"cognee\.infrastructure\.databases\.graph\.config",
    )
    warnings.filterwarnings(
        "ignore",
        message=r"`json_encoders` is deprecated\..*",
        category=PydanticDeprecatedSince20,
        module=r"pydantic\._internal\._generate_schema",
    )
