"""Built-in evaluation engine adapters."""

from __future__ import annotations

from .base import DisabledEvaluationEngine
from .deepeval_engine import DeepEvalEvaluationEngine
from .evalscope_engine import (
    EvalScopeEvaluationEngine,
    EvalScopeSelfHostedSdkEvaluationEngine,
    _build_evalscope_payload,
)
from .utils.common import _default_metric_requests
from .utils.deepeval_helper import (
    OpenAICompatibleDeepEvalModel,
    _build_deepeval_judge_model,
)
from .utils.evalscope_cleaner import _normalize_evalscope_result

__all__ = [
    "DeepEvalEvaluationEngine",
    "DisabledEvaluationEngine",
    "EvalScopeEvaluationEngine",
    "EvalScopeSelfHostedSdkEvaluationEngine",
    "OpenAICompatibleDeepEvalModel",
    "_build_deepeval_judge_model",
    "_build_evalscope_payload",
    "_default_metric_requests",
    "_normalize_evalscope_result",
]
