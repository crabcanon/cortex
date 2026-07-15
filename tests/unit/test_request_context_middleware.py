import pytest
from cortex_api.middleware.request_context import request_context_middleware
from fastapi import Request, Response


@pytest.mark.asyncio
async def test_security_headers() -> None:
    request = Request({"type": "http", "state": {}, "headers": [], "method": "GET", "path": "/"})

    async def call_next(req: Request) -> Response:
        return Response()

    response = await request_context_middleware(request, call_next)

    assert response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
