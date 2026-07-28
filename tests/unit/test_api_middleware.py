import pytest
from cortex_api.middleware.request_context import request_context_middleware
from fastapi import Request, Response


@pytest.mark.asyncio
async def test_request_context_middleware_adds_security_headers():
    request = Request({
        "type": "http",
        "state": {},
        "headers": [],
        "method": "GET",
        "path": "/"
    })

    async def call_next(req: Request) -> Response:
        return Response(content="ok")

    response = await request_context_middleware(request, call_next)

    hsts = response.headers.get("Strict-Transport-Security")
    assert hsts == "max-age=31536000; includeSubDomains"
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"