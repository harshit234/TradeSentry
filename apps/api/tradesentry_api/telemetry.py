from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def configure_telemetry(service_name: str) -> None:
    provider = trace.get_tracer_provider()
    if provider.__class__.__name__ == "ProxyTracerProvider":
        configured = TracerProvider(resource=Resource.create({"service.name": service_name}))
        if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
            configured.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(configured)


@contextmanager
def traced(name: str, **attributes: Any) -> Iterator[None]:
    tracer = trace.get_tracer("tradesentry")
    with tracer.start_as_current_span(name, attributes=attributes):
        yield
