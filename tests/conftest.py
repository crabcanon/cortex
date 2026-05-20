"""Shared pytest configuration for workspace-wide test hygiene."""

from __future__ import annotations

import warnings

try:  # pragma: no cover - depends on installed pydantic version
    from pydantic.warnings import PydanticDeprecatedSince20
except Exception:  # pragma: no cover - fallback for older/newer pydantic
    PydanticDeprecatedSince20 = DeprecationWarning


import os
import pytest

@pytest.fixture(autouse=True, scope="session")
def configure_auth() -> None:
    os.environ["CORTEX_AUTH_JWT_SHARED_SECRET"] = "test-shared-secret"
    os.environ["CORTEX_COGNEE_LLM_MODEL"] = "gpt-4o"
    os.environ["CORTEX_COGNEE_LLM_API_KEY"] = "test-api-key"
    os.environ["OPENROUTER_MODEL_ID"] = "gpt-4o"
    os.environ["OPENROUTER_API_KEY"] = "test-api-key"
    os.environ["OPENROUTER_EMBEDDING_MODEL_ID"] = "text-embedding-3-small"

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
