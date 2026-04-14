"""Prometheus-compatible metrics payload helpers."""

from cortex_common import CortexSettings, utc_now

API_VERSION = "1.0.0-draft"
PROMETHEUS_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


def build_metrics_payload(settings: CortexSettings) -> str:
    """Build a minimal Prometheus exposition payload."""
    telemetry_enabled = "true" if settings.telemetry.enabled else "false"
    now_unix = int(utc_now().timestamp())
    lines = [
        "# HELP cortex_build_info Static Cortex API build information.",
        "# TYPE cortex_build_info gauge",
        (
            'cortex_build_info{service="cortex-api",version="'
            f'{API_VERSION}",telemetry_enabled="{telemetry_enabled}"}} 1'
        ),
        "# HELP cortex_runtime_up Cortex API runtime availability.",
        "# TYPE cortex_runtime_up gauge",
        "cortex_runtime_up 1",
        "# HELP cortex_runtime_timestamp_seconds Current Cortex API unix timestamp.",
        "# TYPE cortex_runtime_timestamp_seconds gauge",
        f"cortex_runtime_timestamp_seconds {now_unix}",
    ]
    return "\n".join(lines) + "\n"
