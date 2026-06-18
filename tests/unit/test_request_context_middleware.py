from unittest.mock import AsyncMock

import pytest
from cortex_api.middleware.request_context import request_context_middleware
from fastapi import Request, Response


@pytest.mark.asyncio
async def test_request_context_middleware_adds_security_headers():
    # Setup mock request
    scope = {"type": "http", "method": "GET", "path": "/path", "headers": [], "state": {}}
    request = Request(scope)

    # Setup mock response
    mock_response = Response()

    # Mock call_next
    call_next = AsyncMock(return_value=mock_response)

    # Mock get_trace_context to return empty trace_id to simplify
    import cortex_observability

    original_get_trace_context = cortex_observability.get_trace_context
    cortex_observability.get_trace_context = lambda: {
        "trace_id": None,
        "span_id": None,
        "trace_flags": None,
    }

    try:
        response = await request_context_middleware(request, call_next)

        assert (
            response.headers.get("Strict-Transport-Security")
            == "max-age=31536000; includeSubDomains"
        )
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert "x-request-id" in response.headers
    finally:
        # Restore original function
        cortex_observability.get_trace_context = original_get_trace_context
