import pytest
from cortex_api.middleware.request_context import request_context_middleware
from fastapi import Request, Response


@pytest.mark.asyncio
async def test_request_context_middleware_adds_security_headers():
    request = Request({"type": "http", "state": {}, "headers": [], "method": "GET", "path": "/"})

    async def mock_call_next(req: Request) -> Response:
        return Response()

    response = await request_context_middleware(request, mock_call_next)

    assert (
        response.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"
    )
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
