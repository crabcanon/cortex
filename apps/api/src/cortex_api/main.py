"""FastAPI entrypoint for Cortex."""

import uvicorn
from fastapi import FastAPI

from .lifespan import lifespan


def create_app() -> FastAPI:
    """Create the FastAPI application instance."""
    return FastAPI(
        title="Cortex API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )


app = create_app()


def run() -> None:
    """Run the local development API server."""
    uvicorn.run("cortex_api.main:app", host="127.0.0.1", port=8080, reload=False)
