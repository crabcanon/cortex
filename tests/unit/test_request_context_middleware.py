import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cortex_api.middleware.request_context import request_context_middleware


@pytest.fixture
def app() -> FastAPI:
    _app = FastAPI()
    _app.middleware("http")(request_context_middleware)

    @_app.get("/")
    def read_root() -> dict[str, str]:
        return {"message": "Hello World"}

    return _app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def test_request_context_middleware_adds_security_headers(client: TestClient) -> None:
    """Verifies that global security headers are applied to responses."""
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"

    # Also verify that it doesn't add Content-Security-Policy globally to not break API docs
    assert "Content-Security-Policy" not in response.headers
