"""OpenTelemetry setup: traces (OTLP), metrics (Prometheus reader) and JSON logs.

Every log line is a JSON object carrying the active ``trace_id`` / ``span_id`` so
that Grafana can jump from a Loki log line to the matching Tempo trace.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import UTC, datetime

from opentelemetry import metrics, trace
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

SERVICE = os.getenv("OTEL_SERVICE_NAME", "payment-api")
VERSION = os.getenv("APP_VERSION", "1.0.0")

_configured = False


class JsonFormatter(logging.Formatter):
    """Structured JSON log formatter enriched with the current trace context."""

    def format(self, record: logging.LogRecord) -> str:
        span_ctx = trace.get_current_span().get_span_context()
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": SERVICE,
            "trace_id": format(span_ctx.trace_id, "032x") if span_ctx.is_valid else None,
            "span_id": format(span_ctx.span_id, "016x") if span_ctx.is_valid else None,
        }
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging() -> logging.Logger:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    # uvicorn access logs are replaced by our own structured request log
    logging.getLogger("uvicorn.access").disabled = True
    return logging.getLogger(SERVICE)


def configure_otel() -> None:
    """Install tracer & meter providers once (idempotent)."""
    global _configured
    if _configured:
        return
    resource = Resource.create({SERVICE_NAME: SERVICE, SERVICE_VERSION: VERSION})

    tracer_provider = TracerProvider(resource=resource)
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:  # pragma: no cover - requires a running collector
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        tracer_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces"))
        )
    trace.set_tracer_provider(tracer_provider)

    # OTel metrics are exposed through the default prometheus_client registry (/metrics)
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[PrometheusMetricReader()]))
    _configured = True
