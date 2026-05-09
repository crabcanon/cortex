from __future__ import annotations

from typing import Annotated

from cortex_client import CortexApiError, CortexConnectionError
from fastapi import Body, FastAPI, HTTPException
from finance_urls import FINANCE_URLS
from models import ExperimentReport, ExperimentRequest
from pipeline import ExperimentPipeline
from render_tensorzero_config import render_config
from settings import load_settings
from tensorzero_client import TensorZeroError

app = FastAPI(
    title="TensorZero Cortex Experiment Example",
    version="0.1.0",
    description=(
        "Runs an adaptive A/B testing pipeline across TensorZero and Cortex Parse, "
        "Storage, Knowledge, and Evaluation APIs."
    ),
)


EXPERIMENT_RUN_EXAMPLES = {
    "full_matrix_async": {
        "summary": "Full matrix with async Docling and async Cortex Eval",
        "description": (
            "Compare the same finance URLs across multiple parse engines, route Docling "
            "through async workers, run every TensorZero model variant, and submit a "
            "multi-case dataset to Cortex Evaluation."
        ),
        "value": {
            "query": (
                "Compare the main macroeconomic, inflation, monetary policy, and "
                "financial stability risks across these sources. Cite source names."
            ),
            "parse": {
                "max_urls": 3,
                "engines": [
                    "auto",
                    "crawl4ai",
                    "markitdown",
                    "llama_parse",
                    "jina_reader",
                    "docling",
                ],
                "mode": "sync",
                "engine_modes": {"docling": "async"},
                "scene": None,
                "timeout_seconds": 1200,
            },
            "knowledge": {
                "enabled": True,
                "search_type": "CHUNKS",
                "top_k": 8,
                "fallback_to_parse_artifacts": True,
                "visualize_graph": True,
                "build_timeout_seconds": 1800,
            },
            "tensorzero": {
                "strategy": "exhaustive",
                "variants": ["openai", "gemini", "kimi"],
                "context_grouping": "by_parse_engine",
                "max_context_chars_per_group": 6000,
                "feedback_enabled": True,
                "include_raw_response": False,
            },
            "evaluation": {
                "enabled": True,
                "mode": "async",
                "engine_id": "deepeval",
                "eval_types": ["rag", "custom"],
                "metric_profile": "deepeval_rag_core",
                "persist_report_object": True,
                "max_cases": 3,
                "max_context_chars_per_case": 4000,
                "async_timeout_seconds": 3600,
            },
        },
    },
    "ollama_local_smoke": {
        "summary": "Local Ollama smoke run",
        "description": (
            "Use one lightweight parse path, one Ollama TensorZero variant, and one "
            "small Cortex Evaluation case so local Ollama can validate the full path "
            "without timing out on a large DeepEval matrix."
        ),
        "value": {
            "query": "Summarize the main inflation and financial stability risks.",
            "parse": {"max_urls": 1, "engines": ["markitdown"], "mode": "sync"},
            "knowledge": {"enabled": False, "fallback_to_parse_artifacts": True},
            "tensorzero": {
                "strategy": "selected",
                "variants": ["ollama"],
                "context_grouping": "combined",
                "max_context_chars_per_group": 3000,
                "feedback_enabled": True,
            },
            "evaluation": {
                "enabled": True,
                "mode": "async",
                "engine_id": "deepeval",
                "eval_types": ["rag"],
                "metric_profile": "deepeval_local_smoke",
                "persist_report_object": True,
                "max_cases": 1,
                "max_context_chars_per_case": 2000,
                "async_timeout_seconds": 3600,
            },
        },
    },
    "adaptive_smoke": {
        "summary": "Small adaptive smoke run",
        "description": (
            "Use one parse engine and let TensorZero adaptive routing choose one variant. "
            "Useful before running a larger model-by-engine matrix."
        ),
        "value": {
            "query": "What are the key financial stability risks in these documents?",
            "parse": {"max_urls": 1, "engines": ["markitdown"], "mode": "sync"},
            "knowledge": {"enabled": False, "fallback_to_parse_artifacts": True},
            "tensorzero": {
                "strategy": "adaptive",
                "context_grouping": "combined",
                "feedback_enabled": True,
            },
            "evaluation": {"enabled": False},
        },
    },
    "legacy_compatible": {
        "summary": "Legacy-compatible flat request",
        "description": "The old MVP fields are still accepted for quick CLI or Swagger tests.",
        "value": {
            "query": "Summarize inflation, growth, and financial stability risks.",
            "max_urls": 2,
            "parse_engines": ["auto", "crawl4ai", "markitdown"],
            "parse_mode": "async",
            "submit_cortex_eval": False,
            "cortex_eval_mode": "sync",
            "run_knowledge_jobs": True,
        },
    },
}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/finance-urls")
def finance_urls() -> list[dict[str, object]]:
    return FINANCE_URLS


@app.post("/tensorzero/render-config")
def render_tensorzero_config() -> dict[str, str]:
    path = render_config()
    return {"path": str(path)}


@app.get("/tensorzero/status")
def tensorzero_status() -> dict[str, object]:
    settings = load_settings()
    pipeline = ExperimentPipeline(settings)
    try:
        status = pipeline.tensorzero.status(timeout_seconds=8, delay_seconds=1)
        return {
            "gateway_url": settings.tensorzero_gateway_url,
            "ready_timeout_seconds": settings.tensorzero_ready_timeout_seconds,
            "status": status,
        }
    except TensorZeroError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "gateway_url": settings.tensorzero_gateway_url,
                "message": str(exc),
            },
        ) from exc
    finally:
        pipeline.close()


@app.get("/cortex/status")
def cortex_status() -> dict[str, object]:
    settings = load_settings()
    pipeline = ExperimentPipeline(settings)
    try:
        status = pipeline.cortex.request("GET", "/v1/health/live", auth=False)
        return {
            "base_url": settings.cortex_base_url,
            "status": status,
        }
    except CortexConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "base_url": settings.cortex_base_url,
                "message": str(exc),
                "hint": (
                    "Start Cortex API first, or set CORTEX_BASE_URL in "
                    "examples/tensorzero-cortex/.env."
                ),
            },
        ) from exc
    except CortexApiError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "base_url": settings.cortex_base_url,
                "message": str(exc),
            },
        ) from exc
    finally:
        pipeline.close()


@app.post("/experiments/run", response_model=ExperimentReport)
def run_experiment(
    request: Annotated[
        ExperimentRequest,
        Body(openapi_examples=EXPERIMENT_RUN_EXAMPLES), # type: ignore
    ],
) -> ExperimentReport:
    settings = load_settings()
    pipeline = ExperimentPipeline(settings)
    try:
        return pipeline.run(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except TensorZeroError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except CortexConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "base_url": settings.cortex_base_url,
                "message": str(exc),
                "hint": (
                    "Start Cortex API first, or set CORTEX_BASE_URL in "
                    "examples/tensorzero-cortex/.env. Try GET /cortex/status "
                    "before POST /experiments/run."
                ),
            },
        ) from exc
    except CortexApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        pipeline.close()
