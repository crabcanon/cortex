"""Health endpoints."""

from typing import Annotated

from cortex_auth import AuthorizationService
from cortex_auth.models import CallerContext
from cortex_common import CortexSettings
from cortex_contracts import HealthResponse
from cortex_db import CortexUnitOfWork, SessionFactory
from fastapi import APIRouter, Depends, Request, Response

from ..dependencies.auth import get_current_caller
from ..dependencies.runtime import (
    get_auth_service,
    get_session_factory,
    get_settings,
    get_uow,
)
from ..services.health import build_liveness, build_readiness

router = APIRouter(prefix="/v1/health", tags=["Health"])


@router.get(
    "/live",
    response_model=HealthResponse,
    operation_id="getLiveness",
    summary="Liveness probe",
)
async def get_liveness(
    request: Request,
    response: Response,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    settings: Annotated[CortexSettings, Depends(get_settings)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
) -> HealthResponse:
    del response
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="health:read",
        request_id=getattr(request.state, "request_id", None),
    )
    return await build_liveness(settings)


@router.get(
    "/ready",
    response_model=HealthResponse,
    operation_id="getReadiness",
    summary="Readiness probe",
    responses={503: {"model": HealthResponse}},
)
async def get_readiness(
    request: Request,
    response: Response,
    caller: Annotated[CallerContext, Depends(get_current_caller)],
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    settings: Annotated[CortexSettings, Depends(get_settings)],
    session_factory: Annotated[SessionFactory, Depends(get_session_factory)],
    uow: Annotated[CortexUnitOfWork, Depends(get_uow)],
) -> HealthResponse:
    await auth_service.authorize(
        uow=uow,
        caller=caller,
        permission_key="health:read",
        request_id=getattr(request.state, "request_id", None),
    )
    status_code, payload = await build_readiness(settings, session_factory)
    response.status_code = status_code
    return payload
