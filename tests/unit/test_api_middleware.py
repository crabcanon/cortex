"""Unit tests for the request context middleware."""

import pytest
from cortex_api.middleware.request_context import request_context_middleware
from fastapi import Request, Response


@pytest.mark.asyncio
async def test_request_context_middleware_adds_security_headers() -> None:
    """Test that the middleware injects security headers."""

    async def mock_call_next(request: Request) -> Response:
        return Response(status_code=200, content="OK")

    scope = {
        "type": "http",
        "method": "GET",
        "url": "http://testserver/",
        "headers": [],
        "query_string": b"",
        "path": "/",
    }
    request = Request(scope)

    response = await request_context_middleware(request, mock_call_next)

    assert response.status_code == 200
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
