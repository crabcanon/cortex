"""Parser profile loading from YAML templates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from cortex_common import ConfigError
from cortex_contracts import (
    FallbackPolicy,
    ParseNormalizationOptions,
    ParserProfile,
    ParserProfileList,
)

from .models import LoadedParserProfile


class ParseProfileLoader:
    """Load reusable parser profiles from a filesystem directory."""

    def __init__(self, base_path: Path | None = None) -> None:
        self._base_path = base_path or Path(__file__).resolve().parent / "profiles"

    def load(self, profile_ref: str) -> LoadedParserProfile:
        profile_path = self._base_path / f"{profile_ref}.yaml"
        if not profile_path.exists():
            raise ConfigError(f"Parser profile `{profile_ref}` was not found.")
        payload = self._load_yaml(profile_path)
        descriptor = ParserProfile(
            profile_ref=str(payload.get("profile_ref", profile_ref)),
            display_name=str(payload.get("display_name", profile_ref)),
            description=self._optional_str(payload.get("description")),
            routing_mode=self._optional_str(payload.get("routing_mode")),
            preferred_engine_key=self._optional_str(payload.get("preferred_engine_key")),
            allowed_engines=self._string_list(payload.get("allowed_engines")),
            normalization_defaults=ParseNormalizationOptions.model_validate(
                payload.get("normalization_defaults", {})
            ),
            fallback_policy=FallbackPolicy.model_validate(payload.get("fallback_policy", {})),
        )
        return LoadedParserProfile(
            descriptor=descriptor,
            source_constraints=self._mapping(payload.get("source_constraints")),
            engine_overrides={
                str(key): self._mapping(value)
                for key, value in self._mapping(payload.get("engine_overrides")).items()
            },
        )

    def list(self) -> ParserProfileList:
        profiles = []
        for path in sorted(self._base_path.glob("*.yaml")):
            profiles.append(self.load(path.stem).descriptor)
        return ParserProfileList(profiles=profiles)

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        if not isinstance(payload, dict):
            raise ConfigError(f"Parser profile `{path.name}` must load to a mapping.")
        return payload

    @staticmethod
    def _mapping(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value]

    @staticmethod
    def _optional_str(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
