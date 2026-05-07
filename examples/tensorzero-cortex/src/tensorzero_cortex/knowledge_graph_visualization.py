from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

from .settings import ARTIFACTS_DIR


class KnowledgeGraphVisualizationError(RuntimeError):
    pass


def latest_run_id() -> str | None:
    if not ARTIFACTS_DIR.exists():
        return None
    candidates = [
        path
        for path in ARTIFACTS_DIR.iterdir()
        if path.is_dir() and path.name.startswith("tzcx_")
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime).name


def visualize_knowledge_graph_from_container(
    *,
    run_id: str | None,
    container_name: str,
    output_name: str = "knowledge_graph.html",
) -> Path:
    resolved_run_id = run_id or latest_run_id()
    if not resolved_run_id:
        raise KnowledgeGraphVisualizationError(
            "No TensorZero Cortex artifact run was found. Pass --run-id explicitly."
        )

    run_dir = ARTIFACTS_DIR / resolved_run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    output_path = run_dir / output_name
    container_output = f"/tmp/cortex_knowledge_graph_{uuid.uuid4().hex}.html"
    script = (
        "import asyncio\n"
        "from cognee.api.v1.visualize.visualize import visualize_graph\n"
        f"asyncio.run(visualize_graph({container_output!r}))\n"
        f"print({container_output!r})\n"
    )

    _run(
        [
            "docker",
            "exec",
            container_name,
            "/app/.venv/bin/python",
            "-c",
            script,
        ],
        action="render Cognee graph visualization in the knowledge worker container",
    )
    _run(
        ["docker", "cp", f"{container_name}:{container_output}", str(output_path)],
        action="copy Cognee graph visualization artifact to the host",
    )
    _run(
        ["docker", "exec", container_name, "rm", "-f", container_output],
        action="remove temporary graph visualization artifact from the container",
        check=False,
    )
    return output_path


def _run(
    command: list[str],
    *,
    action: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(
            command,
            check=check,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise KnowledgeGraphVisualizationError(
            "Docker CLI is not available on PATH. Start Docker Desktop and retry."
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        detail = stderr or stdout or str(exc)
        raise KnowledgeGraphVisualizationError(f"Failed to {action}: {detail}") from exc
    return completed
