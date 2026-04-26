"""Self-hosted API documentation routes."""

from __future__ import annotations

from importlib.resources import files

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from starlette.staticfiles import StaticFiles

_SWAGGER_ASSETS_PATH = str(files("cortex_api").joinpath("static", "swagger-ui"))
_SWAGGER_OAUTH2_REDIRECT_URL = "/docs/oauth2-redirect"
_SWAGGER_UI_VERSION = "5.32.4"
_SWAGGER_ASSETS_URL = f"/_docs/swagger-ui/{_SWAGGER_UI_VERSION}"


def register_docs_routes(app: FastAPI) -> None:
    """Register OpenAPI 3.1-capable Swagger UI without external CDN assets."""

    app.mount(
        _SWAGGER_ASSETS_URL,
        StaticFiles(directory=_SWAGGER_ASSETS_PATH),
        name="swagger-ui-assets",
    )

    @app.get("/docs", include_in_schema=False)
    async def swagger_ui_html():
        response = get_swagger_ui_html(
            openapi_url=app.openapi_url or "/openapi.json",
            title=f"{app.title} - Swagger UI {_SWAGGER_UI_VERSION}",
            oauth2_redirect_url=_SWAGGER_OAUTH2_REDIRECT_URL,
            swagger_js_url=f"{_SWAGGER_ASSETS_URL}/swagger-ui-bundle.js",
            swagger_css_url=f"{_SWAGGER_ASSETS_URL}/swagger-ui.css",
            swagger_favicon_url=f"{_SWAGGER_ASSETS_URL}/favicon-32x32.png",
            swagger_ui_parameters=app.swagger_ui_parameters,
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get(_SWAGGER_OAUTH2_REDIRECT_URL, include_in_schema=False)
    async def swagger_ui_redirect():
        return get_swagger_ui_oauth2_redirect_html()
