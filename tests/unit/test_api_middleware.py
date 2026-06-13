from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from cortex_api.middleware.request_context import request_context_middleware


def test_security_headers() -> None:
    app = FastAPI()
    app.middleware("http")(request_context_middleware)

    @app.get("/")
    def read_root(request: Request) -> JSONResponse:
        return JSONResponse({"message": "Hello World"})

    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
