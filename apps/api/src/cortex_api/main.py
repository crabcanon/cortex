"""FastAPI entrypoint for Cortex."""

import uvicorn
from cortex_common import load_settings
from fastapi import FastAPI

from .errors import register_exception_handlers
from .lifespan import lifespan
from .middleware.request_context import request_context_middleware
from .routers.health import router as health_router
from .routers.jobs import router as jobs_router
from .routers.knowledge import router as knowledge_router
from .routers.observability import router as observability_router
from .routers.parse import router as parse_router
from .routers.storage import router as storage_router


def create_app() -> FastAPI:
    """Create the FastAPI application instance."""
    app = FastAPI(
        title="Cortex API",
        version="1.0.0-draft",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.middleware("http")(request_context_middleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(jobs_router)
    app.include_router(knowledge_router)
    app.include_router(observability_router)
    app.include_router(parse_router)
    app.include_router(storage_router)
    return app


app = create_app()


def run() -> None:
    """Run the local development API server."""
    settings = load_settings().app
    uvicorn.run("cortex_api.main:app", host=settings.host, port=settings.port, reload=False)
