"""Optional OTLP tracing; instrumentation is configured once per service process."""
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def configure_tracing(app, service_name):
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True)))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
    return trace.get_tracer(service_name)
