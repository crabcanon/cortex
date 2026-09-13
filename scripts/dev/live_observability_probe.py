"""Live observability probe against the local OTel/Jaeger/Prometheus stack."""

from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx
from cortex_api.main import create_app
from cortex_common import load_settings
from cortex_contracts import (
    ParseEngineDeploymentMode,
    ParseEngineDescriptor,
    ParseEngineStatus,
)
from cortex_db.cli import main as db_migrate_main
from cortex_parse import (
    EngineExecutionContext,
    EngineExecutionResult,
    ParseEngineProtocol,
    ParseEngineRegistry,
    ParseProfileLoader,
    ParseService,
)
from fastapi.testclient import TestClient


def _dev_bearer_token(*, tenant_id: str, actor_id: str, scopes: list[str]) -> str:
    claims = {
        "sub": actor_id,
        "tenant_id": tenant_id,
        "actor_id": actor_id,
        "actor_ref": f"{actor_id}@example.com",
        "scope": " ".join(scopes),
    }
    encoded = (
        base64.urlsafe_b64encode(json.dumps(claims, separators=(",", ":")).encode("utf-8"))
        .decode("ascii")
        .rstrip("=")
    )
    return f"Bearer dev:{encoded}"


def _case_dir(name: str) -> Path:
    root = Path("runtime-test-data")
    root.mkdir(parents=True, exist_ok=True)
    case_dir = root / f"{name}-{time.time_ns()}"
    case_dir.mkdir(parents=True, exist_ok=True)
    return case_dir


class _ProbeParseEngine(ParseEngineProtocol):
    @property
    def descriptor(self) -> ParseEngineDescriptor:
        return ParseEngineDescriptor(
            engine_key="probe_parse_engine",
            display_name="Probe Parse Engine",
            engine_family="test",
            deployment_mode=ParseEngineDeploymentMode.LOCAL,
            status=ParseEngineStatus.ACTIVE,
            supported_source_types=["url"],
            supported_formats=["text/html"],
            capabilities=["markdown", "metadata"],
        )

    async def execute(self, context: EngineExecutionContext) -> EngineExecutionResult:
        del context
        return EngineExecutionResult(
            markdown="# Probe Page\n\nThe observability probe exercised parse metrics.",
            source_format="text/html",
            detected_mime_type="text/html",
            metadata={
                "title": "Probe Page",
                "language": "en",
                "category_tags": ["probe"],
            },
            final_url="https://example.com/probe",
            http_status=200,
            content_length_bytes=256,
            parser_version="probe-1.0",
            engine_payload_summary={"probe": True},
        )


def _build_parse_service(profiles_dir: Path) -> ParseService:
    registry = ParseEngineRegistry()
    registry.register(_ProbeParseEngine())
    return ParseService(
        registry=registry,
        profile_loader=ParseProfileLoader(profiles_dir),
        default_profile_ref="probe_profile",
    )


def _wait_for_json(url: str, *, timeout_seconds: float = 30.0) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            response = httpx.get(url, timeout=10)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                return payload
        except Exception as exc:  # pragma: no cover - integration probe
            last_error = exc
        time.sleep(1)
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"Timed out waiting for JSON response from {url}")


def _wait_for_trace(trace_id: str, *, timeout_seconds: float = 30.0) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        payload = _wait_for_json(f"http://127.0.0.1:16686/api/traces/{trace_id}", timeout_seconds=5)
        traces = payload.get("data")
        if isinstance(traces, list) and traces:
            return payload
        time.sleep(1)
    raise RuntimeError(f"Timed out waiting for trace {trace_id} in Jaeger")


def _wait_for_metric_name(
    substring: str,
    *,
    timeout_seconds: float = 30.0,
) -> tuple[str, list[str]]:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        metrics_text = httpx.get("http://127.0.0.1:8889/metrics", timeout=10).text
        matching_lines = [line for line in metrics_text.splitlines() if substring in line.lower()]
        if matching_lines:
            return metrics_text, matching_lines
        time.sleep(1)
    raise RuntimeError(f"Timed out waiting for metric containing `{substring}`")


def _wait_for_prometheus_metric_name(
    substring: str,
    *,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        payload = _wait_for_json(
            "http://127.0.0.1:9090/api/v1/label/__name__/values",
            timeout_seconds=5,
        )
        names = payload.get("data")
        if isinstance(names, list) and any(substring in str(name).lower() for name in names):
            return payload
        time.sleep(1)
    raise RuntimeError(f"Timed out waiting for Prometheus metric containing `{substring}`")


def _flush_telemetry(app) -> None:
    runtime = app.state.telemetry
    force_flush = getattr(runtime.tracer_provider, "force_flush", None)
    if callable(force_flush):
        force_flush()
    metric_flush = getattr(runtime.meter_provider, "force_flush", None)
    if callable(metric_flush):
        metric_flush()


def main() -> int:
    case_dir = _case_dir("live-observability")
    db_path = case_dir / "cortex.db"
    profiles_dir = case_dir / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    (profiles_dir / "probe_profile.yaml").write_text(
        "\n".join(
            [
                "profile_ref: probe_profile",
                "display_name: Probe Profile",
                "routing_mode: ordered_fallback",
                "preferred_engine_key: probe_parse_engine",
                "allowed_engines: [probe_parse_engine]",
            ]
        ),
        encoding="utf-8",
    )

    os.environ["CORTEX_DB_DSN"] = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    os.environ["CORTEX_AUTH_MODE"] = "dev"
    os.environ["CORTEX_OTEL_ENABLED"] = "true"
    os.environ["CORTEX_OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://127.0.0.1:4318"
    os.environ["CORTEX_COGNEE_ENABLED"] = "false"
    load_settings.cache_clear()
    db_migrate_main(["upgrade", "head", "--db-url", f"sqlite:///{db_path.as_posix()}"])

    summary: dict[str, Any] = {
        "case_dir": str(case_dir),
        "collector_health": httpx.get("http://127.0.0.1:13133/", timeout=10).json(),
        "prometheus_ready": httpx.get("http://127.0.0.1:9090/-/ready", timeout=10).text.strip(),
    }

    headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_probe",
            actor_id="alice",
            scopes=["health:read", "parse:read", "parse:write"],
        )
    }

    app = create_app()
    with TestClient(app) as client:
        app.state.parse_service = _build_parse_service(profiles_dir)
        health_response = client.get("/v1/health/live", headers=headers)
        parse_response = client.post(
            "/v1/parse/sync",
            headers=headers,
            json={
                "source": {
                    "input_kind": "url",
                    "url": "https://example.com/probe",
                    "expected_content_type": "text/html",
                },
                "parser": {"profile_ref": "probe_profile"},
            },
        )
        metrics_response = client.get("/metrics")
        _flush_telemetry(app)

    trace_id = parse_response.headers.get("x-trace-id")
    if not trace_id:
        raise RuntimeError("Parse probe response did not return x-trace-id")

    jaeger_trace = _wait_for_trace(trace_id)
    collector_metrics_text, collector_metric_lines = _wait_for_metric_name("cortex_parse_requests")
    prometheus_metric_names = _wait_for_prometheus_metric_name("cortex_parse_requests")
    prometheus_up = _wait_for_json(
        "http://127.0.0.1:9090/api/v1/query?query=up%7Bjob%3D%22otel-collector%22%7D",
        timeout_seconds=10,
    )

    summary["health_live"] = {
        "status_code": health_response.status_code,
        "headers": dict(health_response.headers),
        "json": health_response.json(),
    }
    summary["parse_sync"] = {
        "status_code": parse_response.status_code,
        "headers": dict(parse_response.headers),
        "json": parse_response.json(),
    }
    summary["metrics_endpoint"] = {
        "status_code": metrics_response.status_code,
        "headers": dict(metrics_response.headers),
        "text": metrics_response.text,
    }
    summary["jaeger_trace"] = {
        "trace_id": trace_id,
        "trace_count": len(jaeger_trace.get("data", [])),
    }
    summary["collector_metrics"] = {
        "matching_lines": collector_metric_lines[:10],
        "has_cortex_parse_requests": "cortex_parse_requests" in collector_metrics_text.lower(),
    }
    summary["prometheus_metric_names"] = {
        "count": len(prometheus_metric_names.get("data", [])),
        "contains_cortex_parse_requests": any(
            "cortex_parse_requests" in str(name).lower()
            for name in prometheus_metric_names.get("data", [])
        ),
    }
    summary["prometheus_up"] = prometheus_up

    summary_path = case_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    load_settings.cache_clear()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
