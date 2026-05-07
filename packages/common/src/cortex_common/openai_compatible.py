"""Helpers for OpenAI-compatible model provider configuration."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

OPENAI_COMPATIBLE_API_URL_ENV_KEYS = (
    "OPENAI_BASE_URL",
    "OPENAI_API_URL",
    "OPENAI_API_BASE",
    "LITELLM_API_BASE",
)
OPENAI_COMPATIBLE_API_KEY_ENV_KEYS = ("OPENAI_API_KEY", "LITELLM_API_KEY")
OPENAI_COMPATIBLE_OPTION_KEYS = (
    "base_url",
    "api_url",
    "openai_base_url",
    "openai_api_url",
    "api_key",
    "openai_api_key",
)


@dataclass(frozen=True, slots=True)
class OpenAICompatibleConfig:
    """Resolved OpenAI-compatible endpoint and credential values."""

    api_url: str | None = None
    api_key: str | None = None


def resolve_openai_compatible_config(
    *,
    resolve_reference: Callable[[str | None], str | None],
    api_url_ref: str | None = None,
    api_key_ref: str | None = None,
    options: dict[str, Any] | None = None,
) -> OpenAICompatibleConfig:
    """Resolve endpoint/key from runtime references, options, then environment."""

    resolved_options = options or {}
    api_url = resolve_reference(api_url_ref) or _resolve_option_reference(
        resolved_options,
        resolve_reference=resolve_reference,
        keys=("base_url", "api_url", "openai_base_url", "openai_api_url"),
    )
    api_key = resolve_reference(api_key_ref) or _resolve_option_reference(
        resolved_options,
        resolve_reference=resolve_reference,
        keys=("api_key", "openai_api_key"),
    )
    if api_url is None:
        api_url = _first_env(OPENAI_COMPATIBLE_API_URL_ENV_KEYS)
    if api_key is None:
        api_key = _first_env(OPENAI_COMPATIBLE_API_KEY_ENV_KEYS)
    return OpenAICompatibleConfig(
        api_url=_strip(api_url),
        api_key=_strip(api_key),
    )


def apply_openai_compatible_environment(config: OpenAICompatibleConfig) -> None:
    """Expose one provider config through the common env names used by SDKs."""

    if config.api_url:
        for key in OPENAI_COMPATIBLE_API_URL_ENV_KEYS:
            os.environ[key] = config.api_url
    if config.api_key:
        for key in OPENAI_COMPATIBLE_API_KEY_ENV_KEYS:
            os.environ[key] = config.api_key


def strip_openai_compatible_options(options: dict[str, Any]) -> dict[str, Any]:
    """Remove provider endpoint/key aliases before options are exposed downstream."""

    return {
        str(key): value
        for key, value in options.items()
        if str(key) not in OPENAI_COMPATIBLE_OPTION_KEYS
    }


def _resolve_option_reference(
    options: dict[str, Any],
    *,
    resolve_reference: Callable[[str | None], str | None],
    keys: tuple[str, ...],
) -> str | None:
    for key in keys:
        value = options.get(key)
        if isinstance(value, str) and value.strip():
            return resolve_reference(value)
    return None


def _first_env(keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _strip(os.getenv(key))
        if value:
            return value
    return None


def _strip(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
