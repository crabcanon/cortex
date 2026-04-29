"""Synthesis runtime bootstrap helpers."""

from __future__ import annotations

from importlib.util import find_spec

from cortex_common import (
    LoadedRuntimeConfig,
    SynthesisSettings,
    load_runtime_config,
    resolve_openai_compatible_config,
    strip_openai_compatible_options,
)

from .adapters import DeepEvalSynthesisEngine, DisabledSynthesisEngine, SDVSynthesisEngine
from .registry import SynthesisEngineRegistry
from .service import SynthesisService


def build_synthesis_service(
    settings: SynthesisSettings,
    runtime_config: LoadedRuntimeConfig | None = None,
) -> SynthesisService:
    loaded_runtime = runtime_config or load_runtime_config()
    synthesis_runtime = loaded_runtime.config.synthesis
    registry = SynthesisEngineRegistry()

    registry.register(
        SDVSynthesisEngine(
            available=bool(synthesis_runtime.engines.sdv.enabled),
            local_available=find_spec("sdv") is not None,
            options=loaded_runtime.resolve_mapping(synthesis_runtime.engines.sdv.options),
        )
    )
    deepeval_runtime = synthesis_runtime.engines.deepeval
    deepeval_options = loaded_runtime.resolve_mapping(deepeval_runtime.options)
    deepeval_provider_config = resolve_openai_compatible_config(
        resolve_reference=loaded_runtime.resolve_reference,
        api_url_ref=deepeval_runtime.api_url_ref,
        api_key_ref=deepeval_runtime.api_key_ref,
        options=deepeval_options,
    )
    deepeval_options = strip_openai_compatible_options(deepeval_options)
    registry.register(
        DeepEvalSynthesisEngine(
            available=bool(deepeval_runtime.enabled),
            local_available=find_spec("deepeval") is not None,
            model=loaded_runtime.resolve_reference(deepeval_runtime.model_ref),
            provider_config=deepeval_provider_config,
            options=deepeval_options,
        )
    )

    for engine in tuple(registry.list_all()):
        if engine.descriptor.availability_status != "disabled":
            continue
        reason = (
            "Enable the corresponding synthesis runtime engine and install its optional dependency."
        )
        registry.register(DisabledSynthesisEngine(engine.descriptor, reason))

    return SynthesisService(
        registry=registry,
        default_profile_ref=settings.default_profile or synthesis_runtime.default_profile_ref,
    )
