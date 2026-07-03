import pytest
from cortex_api.middleware.request_context import request_context_middleware
from fastapi import Request, Response


@pytest.mark.asyncio
async def test_security_headers_are_added():
    request = Request(
        {
            "type": "http",
            "state": {},
            "headers": [],
            "method": "GET",
            "path": "/",
        }
    )

    async def call_next(req: Request) -> Response:
        return Response(content="test")

    response = await request_context_middleware(request, call_next)

    assert (
        response.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"
    )
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
