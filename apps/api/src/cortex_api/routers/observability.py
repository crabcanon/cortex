"""Observability endpoints."""

from typing import Annotated

from cortex_common import CortexSettings
from fastapi import APIRouter, Depends, Response

from ..dependencies.runtime import get_settings
from ..services.metrics import PROMETHEUS_CONTENT_TYPE, build_metrics_payload

router = APIRouter(tags=["Observability"])


@router.get(
    "/metrics",
    operation_id="getMetrics",
    summary="Prometheus scrape endpoint",
)
async def get_metrics(
    settings: Annotated[CortexSettings, Depends(get_settings)],
) -> Response:
    return Response(
        content=build_metrics_payload(settings),
        media_type=PROMETHEUS_CONTENT_TYPE,
    )
