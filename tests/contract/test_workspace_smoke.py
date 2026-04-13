"""Workspace bootstrap smoke tests."""

from importlib import import_module

from cortex_api.main import create_app


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
