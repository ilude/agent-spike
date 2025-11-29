"""Correlation ID middleware for request tracking."""

import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from opentelemetry import trace


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation IDs to requests and responses.

    Correlation IDs enable tracking requests across services and logs.
    If a request includes X-Correlation-ID header, it will be used.
    Otherwise, a new UUID will be generated.
    """

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process request and add correlation ID.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response with X-Correlation-ID header
        """
        # Get correlation ID from request header or generate new one
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Store in request state for access in handlers
        request.state.correlation_id = correlation_id

        # Add to OpenTelemetry trace context
        span = trace.get_current_span()
        if span:
            span.set_attribute("correlation_id", correlation_id)

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        return response
