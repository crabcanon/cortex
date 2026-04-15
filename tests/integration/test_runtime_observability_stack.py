"""Live observability validation against the localhost Collector stack."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.runtime_stack


if os.getenv("CORTEX_RUNTIME_STACK", "").strip() != "1":
    pytest.skip(
        "runtime observability stack tests require CORTEX_RUNTIME_STACK=1",
        allow_module_level=True,
    )


def test_live_observability_probe_round_trip() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/dev/live_observability_probe.py"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    if result.returncode != 0:
        raise AssertionError(
            "live observability probe failed:\n"
            f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
        )

    payload = json.loads(result.stdout)
    assert payload["health_live"]["status_code"] == 200
    assert payload["parse_sync"]["status_code"] == 200
    assert payload["metrics_endpoint"]["status_code"] == 200
    assert payload["jaeger_trace"]["trace_count"] >= 1
    assert payload["collector_metrics"]["has_cortex_parse_requests"] is True
    assert payload["prometheus_metric_names"]["contains_cortex_parse_requests"] is True
    up_results = payload["prometheus_up"]["data"]["result"]
    assert up_results
    assert up_results[0]["value"][1] == "1"
