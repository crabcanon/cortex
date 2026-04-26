"""Evaluation runtime bootstrap helpers."""

from __future__ import annotations

from importlib.util import find_spec

from cortex_common import EvaluationSettings, LoadedRuntimeConfig, load_runtime_config

from .adapters import (
    DeepEvalEvaluationEngine,
    DisabledEvaluationEngine,
    EvalScopeEvaluationEngine,
    EvalScopeSelfHostedSdkEvaluationEngine,
)
from .registry import EvaluationEngineRegistry
from .service import EvaluationService


def _module_available(module_name: str) -> bool:
    try:
        return find_spec(module_name) is not None
    except ModuleNotFoundError:
        return False


def build_evaluation_service(
    settings: EvaluationSettings,
    runtime_config: LoadedRuntimeConfig | None = None,
) -> EvaluationService:
    loaded_runtime = runtime_config or load_runtime_config()
    registry = EvaluationEngineRegistry()
    eval_runtime = loaded_runtime.config.evaluation

    deepeval_engine = DeepEvalEvaluationEngine(
        available=bool(eval_runtime.engines.deepeval.enabled),
        local_available=_module_available("deepeval"),
        model=loaded_runtime.resolve_reference(eval_runtime.engines.deepeval.model_ref),
        options=loaded_runtime.resolve_mapping(eval_runtime.engines.deepeval.options),
    )
    registry.register(deepeval_engine)

    evalscope_runtime = eval_runtime.engines.evalscope
    if evalscope_runtime.enabled:
        mode = evalscope_runtime.mode.strip().lower()
        if mode == "self_hosted_sdk":
            registry.register(
                EvalScopeSelfHostedSdkEvaluationEngine(
                    host=evalscope_runtime.host,
                    port=evalscope_runtime.port,
                    timeout_seconds=evalscope_runtime.timeout_seconds,
                    headers=loaded_runtime.resolve_mapping(evalscope_runtime.headers),
                    debug=evalscope_runtime.debug,
                    startup_timeout_seconds=evalscope_runtime.startup_timeout_seconds,
                    available=True,
                    local_available=_module_available("evalscope.service"),
                )
            )
        else:
            registry.register(
                EvalScopeEvaluationEngine(
                    base_url=evalscope_runtime.base_url,
                    timeout_seconds=evalscope_runtime.timeout_seconds,
                    headers=loaded_runtime.resolve_mapping(evalscope_runtime.headers),
                    display_name="EvalScope (External HTTP)",
                )
            )
    else:
        registry.register(
            DisabledEvaluationEngine(
                descriptor=EvalScopeEvaluationEngine(
                    base_url=evalscope_runtime.base_url,
                    timeout_seconds=evalscope_runtime.timeout_seconds,
                    headers={},
                ).descriptor.model_copy(update={"availability_status": "disabled"}),
                reason="Enable `evaluation.engines.evalscope.enabled` in runtime config.",
            )
        )

    return EvaluationService(
        registry=registry,
        default_profile_ref=settings.default_profile or eval_runtime.default_profile_ref,
    )
