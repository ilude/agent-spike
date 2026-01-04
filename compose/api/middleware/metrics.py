"""HTTP server metrics middleware for OpenTelemetry.

Emits standard HTTP server metrics compatible with Prometheus:
- http_server_request_duration_seconds (histogram)
- http_server_active_requests (gauge)
- http_server_requests_total (counter)
"""

import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from opentelemetry import metrics


class HTTPServerMetricsMiddleware(BaseHTTPMiddleware):
    """Middleware that records HTTP server metrics via OpenTelemetry.

    Records:
    - http_server_request_duration_seconds: Histogram of request latencies
    - http_server_active_requests: Gauge of in-flight requests
    """

    def __init__(self, app, service_name: str = "api"):
        """Initialize HTTP server metrics middleware.

        Args:
            app: The ASGI application
            service_name: Service identifier (used for logging, not metric labels
                         since service.name is already in resource attributes)
        """
        super().__init__(app)

        # Get meter from global provider (must be set before middleware init)
        meter = metrics.get_meter(__name__)

        # Create histogram for request duration (in seconds)
        self._duration_histogram = meter.create_histogram(
            name="http_server_request_duration_seconds",
            description="HTTP server request duration in seconds",
            unit="s",
        )

        # Create up/down counter for active requests
        self._active_requests = meter.create_up_down_counter(
            name="http_server_active_requests",
            description="Number of active HTTP requests",
            unit="1",
        )

        # Create counter for total requests
        self._request_counter = meter.create_counter(
            name="http_server_requests_total",
            description="Total HTTP requests",
            unit="1",
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and record metrics."""
        # Extract route pattern (use path if no route match)
        route = request.scope.get("route")
        http_route = route.path if route else request.url.path

        # Common attributes (avoiding service_name which conflicts with resource attribute)
        attributes = {
            "http_method": request.method,
            "http_route": http_route,
        }

        # Increment active requests
        self._active_requests.add(1, attributes)

        start_time = time.perf_counter()

        try:
            response = await call_next(request)

            # Add status code to attributes
            attributes["http_status_code"] = str(response.status_code)

            # Record request count
            self._request_counter.add(1, attributes)

            # Record duration
            duration = time.perf_counter() - start_time
            self._duration_histogram.record(duration, attributes)

            return response

        except Exception as e:
            # Record error metrics
            attributes["http_status_code"] = "500"
            attributes["error_type"] = type(e).__name__

            self._request_counter.add(1, attributes)

            duration = time.perf_counter() - start_time
            self._duration_histogram.record(duration, attributes)

            raise

        finally:
            # Decrement active requests (use base attributes without status)
            base_attrs = {
                "http_method": request.method,
                "http_route": http_route,
            }
            self._active_requests.add(-1, base_attrs)
