"""LGTM Stack Client for Agent Analysis.

Provides programmatic access to observability data from:
- Loki (logs via LogQL)
- Prometheus (metrics via PromQL)
- Tempo (traces via HTTP API)

Used by AI agents to query their own performance and make calibration decisions.
"""

import httpx
from datetime import datetime, timedelta
from typing import Any, Optional
from pydantic import BaseModel, Field


class ErrorPattern(BaseModel):
    """Error pattern discovered in logs."""
    message: str
    count: int
    last_seen: datetime
    service_name: str


class PerformanceBottleneck(BaseModel):
    """Performance issue detected in traces/metrics."""
    operation: str
    p95_duration_ms: float
    count: int
    service_name: str


class UsagePattern(BaseModel):
    """API usage pattern from metrics."""
    endpoint: str
    requests_per_hour: float
    avg_duration_ms: float
    error_rate: float


class ServiceHealth(BaseModel):
    """Overall service health summary."""
    service_name: str
    status: str = Field(description="healthy, degraded, or unavailable")
    error_rate: float = Field(description="Percentage of requests with errors")
    avg_response_time_ms: float
    requests_per_minute: float
    issues: list[str] = Field(default_factory=list)


class LGTMClient:
    """Client for querying Loki, Grafana, Tempo, Prometheus (LGTM) stack.

    Provides high-level methods for AI agents to analyze observability data.
    """

    def __init__(
        self,
        loki_url: str = "http://192.168.16.241:3100",
        prometheus_url: str = "http://192.168.16.241:9090",
        tempo_url: str = "http://192.168.16.241:3200",
        timeout: int = 30,
    ):
        """Initialize LGTM client.

        Args:
            loki_url: Loki API endpoint
            prometheus_url: Prometheus API endpoint
            tempo_url: Tempo API endpoint
            timeout: Request timeout in seconds
        """
        self.loki_url = loki_url.rstrip("/")
        self.prometheus_url = prometheus_url.rstrip("/")
        self.tempo_url = tempo_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _query_loki(self, logql: str, limit: int = 100) -> dict[str, Any]:
        """Execute LogQL query against Loki.

        Args:
            logql: LogQL query string
            limit: Maximum number of results

        Returns:
            Query response from Loki API
        """
        url = f"{self.loki_url}/loki/api/v1/query_range"
        params = {
            "query": logql,
            "limit": limit,
            "start": int((datetime.now() - timedelta(hours=24)).timestamp() * 1e9),  # 24h ago
            "end": int(datetime.now().timestamp() * 1e9),
        }
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def _query_prometheus(self, promql: str) -> dict[str, Any]:
        """Execute PromQL query against Prometheus.

        Args:
            promql: PromQL query string

        Returns:
            Query response from Prometheus API
        """
        url = f"{self.prometheus_url}/api/v1/query"
        params = {"query": promql}
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def query_error_patterns(
        self,
        service_name: Optional[str] = None,
        lookback_hours: int = 24,
        min_count: int = 5,
    ) -> list[ErrorPattern]:
        """Query for recurring error patterns in logs.

        Used by agents for outcome tracking and error analysis.

        Args:
            service_name: Filter by service name (default: all services)
            lookback_hours: How far back to search
            min_count: Minimum occurrences to be considered a pattern

        Returns:
            List of error patterns sorted by frequency
        """
        # LogQL query to find errors grouped by message
        service_filter = f'service_name="{service_name}"' if service_name else ""
        logql = f'{{level="error"{", " + service_filter if service_filter else ""}}} | json | line_format "{{.message}}"'

        try:
            result = await self._query_loki(logql, limit=1000)

            # Parse and aggregate errors
            error_counts: dict[str, dict] = {}
            for stream in result.get("data", {}).get("result", []):
                service = stream.get("stream", {}).get("service_name", "unknown")
                for value in stream.get("values", []):
                    timestamp, message = value
                    if message not in error_counts:
                        error_counts[message] = {
                            "count": 0,
                            "last_seen": datetime.fromtimestamp(int(timestamp) / 1e9),
                            "service_name": service,
                        }
                    error_counts[message]["count"] += 1

            # Filter and convert to models
            patterns = [
                ErrorPattern(message=msg, **data)
                for msg, data in error_counts.items()
                if data["count"] >= min_count
            ]
            return sorted(patterns, key=lambda p: p.count, reverse=True)

        except Exception as e:
            print(f"Error querying error patterns: {e}")
            return []

    async def query_performance_bottlenecks(
        self,
        service_name: Optional[str] = None,
        p95_threshold_ms: float = 1000,
    ) -> list[PerformanceBottleneck]:
        """Query for slow operations using Prometheus metrics.

        Used by agents for judgment/calibration - identifying slow operations.

        Args:
            service_name: Filter by service name
            p95_threshold_ms: Minimum P95 latency to be considered slow

        Returns:
            List of slow operations
        """
        # PromQL to get P95 latency by operation
        service_filter = f'service_name="{service_name}"' if service_name else ""
        promql = (
            f'histogram_quantile(0.95, '
            f'sum by(operation, service_name, le) '
            f'(rate(http_request_duration_seconds_bucket{{{service_filter}}}[5m])))'
        )

        try:
            result = await self._query_prometheus(promql)

            bottlenecks = []
            for metric in result.get("data", {}).get("result", []):
                operation = metric.get("metric", {}).get("operation", "unknown")
                service = metric.get("metric", {}).get("service_name", "unknown")
                p95_seconds = float(metric.get("value", [0, 0])[1])
                p95_ms = p95_seconds * 1000

                if p95_ms >= p95_threshold_ms:
                    bottlenecks.append(
                        PerformanceBottleneck(
                            operation=operation,
                            p95_duration_ms=p95_ms,
                            count=1,  # Could be enhanced with request count
                            service_name=service,
                        )
                    )

            return sorted(bottlenecks, key=lambda b: b.p95_duration_ms, reverse=True)

        except Exception as e:
            print(f"Error querying performance bottlenecks: {e}")
            return []

    async def query_usage_patterns(
        self,
        service_name: Optional[str] = None,
        top_n: int = 10,
    ) -> list[UsagePattern]:
        """Query API usage patterns from metrics.

        Used by agents for understanding user behavior and API usage.

        Args:
            service_name: Filter by service name
            top_n: Return top N endpoints by request count

        Returns:
            List of usage patterns sorted by request volume
        """
        # PromQL to get request rate by endpoint
        service_filter = f'service_name="{service_name}"' if service_name else ""
        promql = (
            f'topk({top_n}, '
            f'sum by(endpoint, service_name) '
            f'(rate(http_requests_total{{{service_filter}}}[1h]) * 3600))'  # requests per hour
        )

        try:
            result = await self._query_prometheus(promql)

            patterns = []
            for metric in result.get("data", {}).get("result", []):
                endpoint = metric.get("metric", {}).get("endpoint", "unknown")
                service = metric.get("metric", {}).get("service_name", "unknown")
                requests_per_hour = float(metric.get("value", [0, 0])[1])

                # Get avg duration and error rate for this endpoint
                avg_duration_ms = 0.0  # TODO: Query separately
                error_rate = 0.0  # TODO: Query separately

                patterns.append(
                    UsagePattern(
                        endpoint=endpoint,
                        requests_per_hour=requests_per_hour,
                        avg_duration_ms=avg_duration_ms,
                        error_rate=error_rate,
                    )
                )

            return patterns

        except Exception as e:
            print(f"Error querying usage patterns: {e}")
            return []

    async def query_service_health(
        self,
        service_name: str = "agent-spike-api",
    ) -> ServiceHealth:
        """Get comprehensive health summary for a service.

        Combines metrics from multiple sources to provide overall health status.

        Args:
            service_name: Service to check

        Returns:
            Service health summary
        """
        try:
            # Query error rate
            error_rate_promql = (
                f'sum(rate(http_requests_total{{service_name="{service_name}", status_code=~"5.."}}[5m])) / '
                f'sum(rate(http_requests_total{{service_name="{service_name}"}}[5m])) * 100'
            )
            error_result = await self._query_prometheus(error_rate_promql)
            error_rate = float(error_result.get("data", {}).get("result", [{}])[0].get("value", [0, 0])[1])

            # Query avg response time
            latency_promql = (
                f'avg(rate(http_request_duration_seconds_sum{{service_name="{service_name}"}}[5m]) / '
                f'rate(http_request_duration_seconds_count{{service_name="{service_name}"}}[5m])) * 1000'
            )
            latency_result = await self._query_prometheus(latency_promql)
            avg_response_time_ms = float(latency_result.get("data", {}).get("result", [{}])[0].get("value", [0, 0])[1])

            # Query request rate
            rate_promql = f'sum(rate(http_requests_total{{service_name="{service_name}"}}[1m])) * 60'
            rate_result = await self._query_prometheus(rate_promql)
            requests_per_minute = float(rate_result.get("data", {}).get("result", [{}])[0].get("value", [0, 0])[1])

            # Determine status
            issues = []
            if error_rate > 5:
                issues.append(f"High error rate: {error_rate:.2f}%")
            if avg_response_time_ms > 2000:
                issues.append(f"Slow response time: {avg_response_time_ms:.0f}ms")
            if requests_per_minute == 0:
                issues.append("No traffic")

            status = "healthy"
            if issues:
                status = "degraded" if error_rate < 10 else "unavailable"

            return ServiceHealth(
                service_name=service_name,
                status=status,
                error_rate=error_rate,
                avg_response_time_ms=avg_response_time_ms,
                requests_per_minute=requests_per_minute,
                issues=issues,
            )

        except Exception as e:
            return ServiceHealth(
                service_name=service_name,
                status="unavailable",
                error_rate=0,
                avg_response_time_ms=0,
                requests_per_minute=0,
                issues=[f"Failed to query metrics: {str(e)}"],
            )
