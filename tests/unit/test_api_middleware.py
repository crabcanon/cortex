from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from cortex_api.middleware.request_context import request_context_middleware

app = FastAPI()
app.middleware("http")(request_context_middleware)


@app.get("/test")
async def test_route():
    return JSONResponse(content={"message": "ok"})


client = TestClient(app)


def test_security_headers_present():
    """Test that security headers are injected into the response."""
    response = client.get("/test")

    assert response.status_code == 200
    assert response.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
