"""OpenTelemetry tracing, metrics, and logging configuration for LGTM stack."""

import os
import logging
from typing import Optional

from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry._logs import set_logger_provider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor


def setup_tracing(
    service_name: str,
    otlp_endpoint: Optional[str] = None,
    enable_instrumentation: bool = True,
) -> trace.Tracer:
    """Configure OpenTelemetry tracing for SigNoz.

    Args:
        service_name: Name of the service (e.g., "api", "worker")
        otlp_endpoint: OTLP gRPC endpoint (default: from OTLP_ENDPOINT env var)
        enable_instrumentation: Whether to auto-instrument FastAPI and httpx

    Returns:
        Tracer instance
    """
    # Get OTLP endpoint from environment or use default
    if otlp_endpoint is None:
        otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://192.168.16.241:4318")

    # Create resource with service name
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.namespace": "agent-spike",
            "deployment.environment": os.getenv("ENVIRONMENT", "production"),
        }
    )

    # Create trace provider
    provider = TracerProvider(resource=resource)

    # Create OTLP span exporter (HTTP)
    span_exporter = OTLPSpanExporter(
        endpoint=f"{otlp_endpoint}/v1/traces",
    )

    # Add batch processor
    processor = BatchSpanProcessor(span_exporter)
    provider.add_span_processor(processor)

    # Set global trace provider
    trace.set_tracer_provider(provider)

    # Auto-instrument frameworks if enabled
    if enable_instrumentation:
        # Auto-instrument FastAPI
        FastAPIInstrumentor().instrument()

        # Auto-instrument httpx client
        HTTPXClientInstrumentor().instrument()

        # Auto-instrument logging (adds trace context to logs)
        LoggingInstrumentor().instrument()

    # Return tracer for manual instrumentation
    return trace.get_tracer(__name__)


def setup_metrics(
    service_name: str,
    otlp_endpoint: Optional[str] = None,
    export_interval_millis: int = 60000,
) -> metrics.Meter:
    """Configure OpenTelemetry metrics for SigNoz.

    Args:
        service_name: Name of the service (e.g., "api", "worker")
        otlp_endpoint: OTLP gRPC endpoint (default: from OTLP_ENDPOINT env var)
        export_interval_millis: Metric export interval in milliseconds

    Returns:
        Meter instance
    """
    # Get OTLP endpoint from environment or use default
    if otlp_endpoint is None:
        otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://192.168.16.241:4318")

    # Create resource with service name
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.namespace": "agent-spike",
            "deployment.environment": os.getenv("ENVIRONMENT", "production"),
        }
    )

    # Create metric exporter (HTTP)
    metric_exporter = OTLPMetricExporter(
        endpoint=f"{otlp_endpoint}/v1/metrics",
    )

    # Create periodic metric reader
    metric_reader = PeriodicExportingMetricReader(
        metric_exporter,
        export_interval_millis=export_interval_millis,
    )

    # Create meter provider
    provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader],
    )

    # Set global meter provider
    metrics.set_meter_provider(provider)

    # Return meter for custom metrics
    return metrics.get_meter(__name__)


def setup_logging_export(
    service_name: str,
    otlp_endpoint: Optional[str] = None,
    log_level: int = logging.INFO,
) -> LoggerProvider:
    """Configure OpenTelemetry log export to LGTM stack.

    Args:
        service_name: Name of the service (e.g., "api", "worker")
        otlp_endpoint: OTLP HTTP endpoint (default: from OTLP_ENDPOINT env var)
        log_level: Minimum log level to export

    Returns:
        LoggerProvider instance
    """
    # Get OTLP endpoint from environment or use default (HTTP port 4318)
    if otlp_endpoint is None:
        otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://192.168.16.241:4318")

    # Create resource with service name
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.namespace": "agent-spike",
            "deployment.environment": os.getenv("ENVIRONMENT", "production"),
        }
    )

    # Create log exporter (HTTP)
    log_exporter = OTLPLogExporter(
        endpoint=f"{otlp_endpoint}/v1/logs",
    )

    # Create logger provider
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))

    # Set global logger provider
    set_logger_provider(logger_provider)

    # Create handler that sends logs to OTLP
    handler = LoggingHandler(
        level=log_level,
        logger_provider=logger_provider,
    )

    # Add handler to root logger
    logging.getLogger().addHandler(handler)

    return logger_provider


def setup_telemetry(
    service_name: str,
    otlp_endpoint: Optional[str] = None,
    enable_instrumentation: bool = True,
    enable_logs: bool = True,
) -> tuple[trace.Tracer, metrics.Meter]:
    """Configure tracing, metrics, and logging for LGTM stack.

    Args:
        service_name: Name of the service (e.g., "api", "worker")
        otlp_endpoint: OTLP HTTP endpoint (default: from OTLP_ENDPOINT env var)
        enable_instrumentation: Whether to auto-instrument FastAPI and httpx
        enable_logs: Whether to export logs via OTLP

    Returns:
        Tuple of (tracer, meter) instances
    """
    tracer = setup_tracing(service_name, otlp_endpoint, enable_instrumentation)
    meter = setup_metrics(service_name, otlp_endpoint)

    if enable_logs:
        setup_logging_export(service_name, otlp_endpoint)

    return tracer, meter


# Convenience decorator for tracing functions
def traced(name: Optional[str] = None):
    """Decorator to add tracing to a function.

    Args:
        name: Optional span name (defaults to function name)

    Example:
        @traced("my_operation")
        async def my_function():
            ...
    """

    def decorator(func):
        span_name = name or func.__name__
        tracer = trace.get_tracer(__name__)

        if asyncio.iscoroutinefunction(func):

            async def async_wrapper(*args, **kwargs):
                with tracer.start_as_current_span(span_name):
                    return await func(*args, **kwargs)

            return async_wrapper
        else:

            def wrapper(*args, **kwargs):
                with tracer.start_as_current_span(span_name):
                    return func(*args, **kwargs)

            return wrapper

    return decorator


# Import asyncio for decorator
import asyncio
