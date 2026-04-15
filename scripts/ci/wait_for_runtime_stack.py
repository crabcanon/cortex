"""Wait for the local Cortex runtime stack to become ready."""

from __future__ import annotations

import argparse
import os
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Probe:
    name: str
    kind: str
    target: str
    timeout_seconds: int


def _env(name: str, default: str) -> str:
    return os.getenv(name, default).strip() or default


def _build_probes(timeout_seconds: int) -> list[Probe]:
    postgres_host = _env("CORTEX_STACK_POSTGRES_HOST", "127.0.0.1")
    postgres_port = _env("CORTEX_STACK_POSTGRES_PORT", "5432")
    minio_endpoint = _env("CORTEX_STACK_MINIO_ENDPOINT", "http://127.0.0.1:9000")
    redis_host = _env("CORTEX_STACK_REDIS_HOST", "127.0.0.1")
    redis_port = _env("CORTEX_STACK_REDIS_PORT", "6379")
    otel_health = _env("CORTEX_STACK_OTEL_HEALTH_URL", "http://127.0.0.1:13133/")
    jaeger_url = _env("CORTEX_STACK_JAEGER_URL", "http://127.0.0.1:16686/")
    prometheus_url = _env("CORTEX_STACK_PROMETHEUS_READY_URL", "http://127.0.0.1:9090/-/ready")
    grafana_url = _env("CORTEX_STACK_GRAFANA_HEALTH_URL", "http://127.0.0.1:3000/api/health")

    return [
        Probe("postgres", "tcp", f"{postgres_host}:{postgres_port}", timeout_seconds),
        Probe(
            "minio",
            "http",
            f"{minio_endpoint.rstrip('/')}/minio/health/ready",
            timeout_seconds,
        ),
        Probe("redis", "tcp", f"{redis_host}:{redis_port}", timeout_seconds),
        Probe("otel-collector", "http", otel_health, timeout_seconds),
        Probe("jaeger", "http", jaeger_url, timeout_seconds),
        Probe("prometheus", "http", prometheus_url, timeout_seconds),
        Probe("grafana", "http", grafana_url, timeout_seconds),
    ]


def _wait_for_tcp(target: str, timeout_seconds: int) -> None:
    host, port_text = target.rsplit(":", maxsplit=1)
    port = int(port_text)
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=3):
                return
        except OSError as exc:
            last_error = exc
            time.sleep(2)
    raise TimeoutError(f"Timed out waiting for TCP probe {target}: {last_error}")


def _wait_for_http(target: str, timeout_seconds: int) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(target, timeout=5) as response:
                if 200 <= response.status < 500:
                    return
                last_error = RuntimeError(f"unexpected HTTP status {response.status}")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
        time.sleep(2)
    raise TimeoutError(f"Timed out waiting for HTTP probe {target}: {last_error}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Wait for the docker-backed Cortex runtime stack to become ready."
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=120,
        help="Timeout budget applied to each readiness probe.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    for probe in _build_probes(args.timeout_seconds):
        print(f"[cortex] waiting for {probe.name} ({probe.kind}: {probe.target})...")
        if probe.kind == "tcp":
            _wait_for_tcp(probe.target, probe.timeout_seconds)
        else:
            _wait_for_http(probe.target, probe.timeout_seconds)
        print(f"[cortex] {probe.name} is ready.")
    print("[cortex] runtime stack is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
