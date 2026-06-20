"""Unit tests for the request context middleware."""

import pytest
from cortex_api.middleware.request_context import request_context_middleware
from cortex_contracts import X_REQUEST_ID_HEADER
from fastapi import Request, Response


@pytest.mark.asyncio
async def test_request_context_middleware_adds_security_headers():
    """Verify that security headers are added to the API responses."""
    # Create a mock request
    scope = {"type": "http", "state": {}, "method": "GET", "path": "/test", "headers": []}
    request = Request(scope)

    # Create a mock response
    mock_response = Response(content="test")

    # Create a mock call_next function
    async def call_next(req: Request) -> Response:
        return mock_response

    # Call the middleware
    response = await request_context_middleware(request, call_next)

    # Verify the response
    assert response is mock_response

    # Verify that the security headers are present
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"

    # Verify that the request ID header is present
    assert X_REQUEST_ID_HEADER in response.headers
