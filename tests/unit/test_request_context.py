import pytest
from unittest.mock import MagicMock
from fastapi import Request, Response
from cortex_api.middleware.request_context import request_context_middleware
from cortex_contracts import X_REQUEST_ID_HEADER, X_TRACE_ID_HEADER

@pytest.mark.asyncio
async def test_request_context_middleware_adds_security_headers():
    # Arrange
    request = Request({"type": "http", "state": {}, "headers": [], "method": "GET", "path": "/"})

    async def mock_call_next(req: Request) -> Response:
        return Response()

    # Act
    response = await request_context_middleware(request, mock_call_next)

    # Assert
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert X_REQUEST_ID_HEADER in response.headers
