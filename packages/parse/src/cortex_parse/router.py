"""Parse engine routing and fallback selection."""

from __future__ import annotations

from cortex_common import ConfigError, ValidationError
from cortex_contracts import (
    FallbackMode,
    ParseEngineDescriptor,
    ParseEngineStatus,
    ParseInputKind,
    ParseSyncRequest,
)
from opentelemetry import trace

from .models import LoadedParserProfile, RoutedParseEngine, RouterSelection
from .profile_loader import ParseProfileLoader
from .registry import ParseEngineRegistry


class ParseRouter:
    """Select registered parse engines based on request and profile strategy."""

    def __init__(
        self,
        registry: ParseEngineRegistry,
        profile_loader: ParseProfileLoader,
        *,
        default_profile_ref: str | None = None,
    ) -> None:
        self._registry = registry
        self._profile_loader = profile_loader
        self._default_profile_ref = default_profile_ref
        self._tracer = trace.get_tracer("cortex.parse.router")

    def resolve(self, request: ParseSyncRequest) -> RouterSelection:
        with self._tracer.start_as_current_span("parse.router.select") as span:
            profile = self._resolve_profile(request)
            fallback_policy = self._resolve_fallback_policy(request, profile)
            active_descriptors = self._registry.descriptors()
            descriptors = self._filter_supported(active_descriptors, request)
            allowed = request.parser.allowed_engines or (
                profile.descriptor.allowed_engines if profile else []
            )
            if allowed:
                allowed_set = set(allowed)
                descriptors = [
                    descriptor
                    for descriptor in descriptors
                    if descriptor.engine_key in allowed_set
                ]
            preferred = request.parser.preferred_engine_key or (
                profile.descriptor.preferred_engine_key if profile else None
            )
            ordered = self._order_descriptors(descriptors, preferred, allowed)
            if (
                not fallback_policy.enabled or fallback_policy.mode is FallbackMode.NONE
            ) and ordered:
                ordered = ordered[:1]
            ordered = ordered[: fallback_policy.max_engine_attempts]
            engines = [
                RoutedParseEngine(
                    descriptor=descriptor,
                    engine=self._require_engine(descriptor.engine_key),
                    engine_options=self._merge_engine_options(
                        request,
                        profile,
                        descriptor.engine_key,
                    ),
                )
                for descriptor in ordered
            ]
            if not engines:
                raise ValidationError("No active parse engine can handle the requested source.")
            span.set_attribute(
                "cortex.parse.profile",
                profile.descriptor.profile_ref if profile else "",
            )
            span.set_attribute("cortex.parse.candidate_count", len(engines))
            span.set_attribute("cortex.parse.source_kind", request.source.input_kind.value)
            return RouterSelection(
                profile=profile,
                engines=engines,
                fallback_policy=fallback_policy,
                fallback_used=len(engines) > 1,
            )

    def list_profiles(self):
        return self._profile_loader.list()

    def list_engines(self):
        return self._registry.list()

    def _resolve_profile(self, request: ParseSyncRequest) -> LoadedParserProfile | None:
        profile_ref = request.parser.profile_ref or self._default_profile_ref
        if profile_ref is None:
            return None
        return self._profile_loader.load(profile_ref)

    @staticmethod
    def _resolve_fallback_policy(
        request: ParseSyncRequest,
        profile: LoadedParserProfile | None,
    ):
        request_policy = request.parser.fallback_policy
        if profile is None:
            return request_policy
        if request_policy.model_dump() == request_policy.__class__().model_dump():
            return profile.descriptor.fallback_policy
        return request_policy

    def _filter_supported(
        self,
        descriptors: list[ParseEngineDescriptor],
        request: ParseSyncRequest,
    ) -> list[ParseEngineDescriptor]:
        return [
            descriptor
            for descriptor in descriptors
            if descriptor.status is ParseEngineStatus.ACTIVE
            and self._supports_source(descriptor, request.source.input_kind)
            and self._supports_content_type(descriptor, request.source.expected_content_type)
        ]

    @staticmethod
    def _supports_source(descriptor: ParseEngineDescriptor, input_kind: ParseInputKind) -> bool:
        if not descriptor.supported_source_types:
            return True
        return input_kind.value in descriptor.supported_source_types

    @staticmethod
    def _supports_content_type(
        descriptor: ParseEngineDescriptor,
        expected_content_type: str | None,
    ) -> bool:
        if not expected_content_type or not descriptor.supported_formats:
            return True
        for supported in descriptor.supported_formats:
            if supported == expected_content_type:
                return True
            if supported.endswith("/*") and expected_content_type.startswith(supported[:-1]):
                return True
        return False

    @staticmethod
    def _order_descriptors(
        descriptors: list[ParseEngineDescriptor],
        preferred_engine_key: str | None,
        allowed_engines: list[str],
    ) -> list[ParseEngineDescriptor]:
        by_key = {descriptor.engine_key: descriptor for descriptor in descriptors}
        ordered_keys: list[str] = []
        if preferred_engine_key:
            ordered_keys.append(preferred_engine_key)
        ordered_keys.extend(allowed_engines)
        ordered_keys.extend(descriptor.engine_key for descriptor in descriptors)
        seen: set[str] = set()
        ordered: list[ParseEngineDescriptor] = []
        for engine_key in ordered_keys:
            if engine_key in seen:
                continue
            descriptor = by_key.get(engine_key)
            if descriptor is None:
                continue
            seen.add(engine_key)
            ordered.append(descriptor)
        return ordered

    def _require_engine(self, engine_key: str):
        engine = self._registry.get(engine_key)
        if engine is None:
            raise ConfigError(f"Registered parse engine `{engine_key}` has no implementation.")
        return engine

    @staticmethod
    def _merge_engine_options(
        request: ParseSyncRequest,
        profile: LoadedParserProfile | None,
        engine_key: str,
    ) -> dict[str, object]:
        merged: dict[str, object] = {}
        if profile is not None:
            merged.update(profile.engine_overrides.get(engine_key, {}))
        merged.update(request.parser.engine_options)
        return merged
