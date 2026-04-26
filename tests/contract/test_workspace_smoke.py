"""Workspace bootstrap smoke tests."""

from importlib import import_module

from cortex_api.main import create_app
from fastapi.testclient import TestClient


def test_workspace_packages_import() -> None:
    package_names = [
        "cortex_api",
        "cortex_worker_parse",
        "cortex_worker_knowledge",
        "cortex_common",
        "cortex_contracts",
        "cortex_domain",
        "cortex_db",
        "cortex_auth",
        "cortex_storage",
        "cortex_parse",
        "cortex_knowledge",
        "cortex_observability",
    ]

    for package_name in package_names:
        module = import_module(package_name)
        assert module is not None


def test_fastapi_app_bootstrap() -> None:
    app = create_app()
    assert app.title == "Cortex API"
    assert app.openapi_url == "/openapi.json"
    assert app.openapi_version == "3.1.0"


def test_swagger_ui_uses_self_hosted_assets() -> None:
    client = TestClient(create_app())

    docs_response = client.get("/docs")
    assert docs_response.status_code == 200
    assert "https://cdn.jsdelivr.net" not in docs_response.text
    assert "Swagger UI 5.32.4" in docs_response.text
    assert docs_response.headers["cache-control"] == "no-store"
    assert "/_docs/swagger-ui/5.32.4/swagger-ui-bundle.js" in docs_response.text
    assert "/_docs/swagger-ui/5.32.4/swagger-ui.css" in docs_response.text

    openapi_response = client.get("/openapi.json")
    assert openapi_response.status_code == 200
    assert openapi_response.json()["openapi"] == "3.1.0"

    js_response = client.get("/_docs/swagger-ui/5.32.4/swagger-ui-bundle.js")
    assert js_response.status_code == 200
    assert "SwaggerUIBundle" in js_response.text
