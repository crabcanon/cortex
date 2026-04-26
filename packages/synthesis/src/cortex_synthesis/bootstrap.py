"""Synthesis runtime bootstrap helpers."""

from __future__ import annotations

from importlib.util import find_spec

from cortex_common import LoadedRuntimeConfig, SynthesisSettings, load_runtime_config

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
    registry.register(
        DeepEvalSynthesisEngine(
            available=bool(synthesis_runtime.engines.deepeval.enabled),
            local_available=find_spec("deepeval") is not None,
            model=loaded_runtime.resolve_reference(
                synthesis_runtime.engines.deepeval.model_ref
            ),
            options=loaded_runtime.resolve_mapping(synthesis_runtime.engines.deepeval.options),
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
