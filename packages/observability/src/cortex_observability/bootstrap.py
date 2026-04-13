"""OpenTelemetry bootstrap helpers."""

from dataclasses import dataclass

from cortex_common.settings import TelemetrySettings
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


@dataclass(slots=True)
class TelemetryRuntime:
    tracer_provider: TracerProvider
    meter_provider: MeterProvider


_telemetry_runtime: TelemetryRuntime | None = None


def configure_telemetry(
    service_name: str,
    settings: TelemetrySettings,
    *,
    service_version: str = "0.1.0",
) -> TelemetryRuntime:
    """Configure tracer and meter providers for a Cortex process."""
    global _telemetry_runtime

    if _telemetry_runtime is not None:
        return _telemetry_runtime

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment.name": settings.deployment_env,
            "cortex.region": settings.region,
            "cortex.cluster": settings.cluster,
        }
    )

    tracer_provider = TracerProvider(resource=resource)
    if settings.enabled and settings.exporter_otlp_endpoint:
        endpoint = settings.exporter_otlp_endpoint.rstrip("/")
        if not endpoint.endswith("/v1/traces"):
            endpoint = f"{endpoint}/v1/traces"
        exporter = OTLPSpanExporter(endpoint=endpoint)
        tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(tracer_provider)

    meter_provider = MeterProvider(resource=resource)
    metrics.set_meter_provider(meter_provider)

    _telemetry_runtime = TelemetryRuntime(
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
    )
    return _telemetry_runtime
