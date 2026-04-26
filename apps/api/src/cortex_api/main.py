"""FastAPI entrypoint for Cortex."""

import uvicorn
from cortex_common import CortexSettings, load_settings
from fastapi import FastAPI

from .docs import register_docs_routes
from .errors import register_exception_handlers
from .lifespan import lifespan
from .middleware.request_context import request_context_middleware
from .routers.dev_auth import router as dev_auth_router
from .routers.evaluation import router as evaluation_router
from .routers.health import router as health_router
from .routers.jobs import router as jobs_router
from .routers.knowledge import router as knowledge_router
from .routers.observability import router as observability_router
from .routers.parse import router as parse_router
from .routers.storage import router as storage_router
from .routers.synthesis import router as synthesis_router


def _local_dev_token_route_enabled(settings: CortexSettings) -> bool:
    return (
        settings.app.environment.strip().lower() == "local"
        and settings.auth.mode.strip().lower() == "dev"
    )


def create_app() -> FastAPI:
    """Create the FastAPI application instance."""
    settings = load_settings()
    app = FastAPI(
        title="Cortex API",
        version="1.0.0-draft",
        lifespan=lifespan,
        docs_url=None,
        openapi_version="3.1.0",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    register_docs_routes(app)
    app.middleware("http")(request_context_middleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(jobs_router)
    app.include_router(evaluation_router)
    app.include_router(knowledge_router)
    app.include_router(observability_router)
    app.include_router(parse_router)
    app.include_router(storage_router)
    app.include_router(synthesis_router)
    if _local_dev_token_route_enabled(settings):
        app.include_router(dev_auth_router)
    return app


app = create_app()


def run() -> None:
    """Run the local development API server."""
    settings = load_settings().app
    uvicorn.run("cortex_api.main:app", host=settings.host, port=settings.port, reload=False)
