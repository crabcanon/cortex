from unittest.mock import AsyncMock

import pytest
from cortex_api.middleware.request_context import request_context_middleware
from fastapi import Request, Response


@pytest.mark.asyncio
async def test_request_context_middleware_adds_security_headers():
    request = Request({"type": "http", "state": {}, "headers": [], "method": "GET", "path": "/"})
    mock_response = Response(status_code=200)
    call_next = AsyncMock(return_value=mock_response)

    response = await request_context_middleware(request, call_next)

    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
