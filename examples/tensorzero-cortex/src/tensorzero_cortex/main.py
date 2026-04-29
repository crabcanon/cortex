from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .cortex_client import CortexApiError
from .finance_urls import FINANCE_URLS
from .models import ExperimentReport, ExperimentRequest
from .pipeline import ExperimentPipeline
from .render_tensorzero_config import render_config
from .settings import load_settings
from .tensorzero_client import TensorZeroError

app = FastAPI(
    title="TensorZero Cortex Experiment Example",
    version="0.1.0",
    description=(
        "Runs an adaptive A/B testing pipeline across TensorZero and Cortex Parse, "
        "Storage, Knowledge, and Evaluation APIs."
    ),
)


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


@app.post("/experiments/run", response_model=ExperimentReport)
def run_experiment(request: ExperimentRequest) -> ExperimentReport:
    pipeline = ExperimentPipeline(load_settings())
    try:
        return pipeline.run(request)
    except TensorZeroError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except CortexApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        pipeline.close()
