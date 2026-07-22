from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path

from settings import ARTIFACTS_DIR


class KnowledgeGraphVisualizationError(RuntimeError):
    pass


def latest_run_id() -> str | None:
    if not ARTIFACTS_DIR.exists():
        return None
    candidates = [
        path for path in ARTIFACTS_DIR.iterdir() if path.is_dir() and path.name.startswith("tzcx_")
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime).name


def visualize_knowledge_graph_from_container(
    *,
    run_id: str | None,
    container_name: str,
    dataset_key: str | None = None,
    output_name: str = "knowledge_graph.html",
) -> Path:
    resolved_run_id = run_id or latest_run_id()
    if not resolved_run_id:
        raise KnowledgeGraphVisualizationError(
            "No TensorZero Cortex artifact run was found. Pass --run-id explicitly."
        )

    run_dir = ARTIFACTS_DIR / resolved_run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    resolved_dataset_key = _resolve_dataset_key(
        run_dir=run_dir,
        run_id=resolved_run_id,
        dataset_key=dataset_key,
    )
    output_path = run_dir / output_name
    container_output = f"/tmp/cortex_knowledge_graph_{uuid.uuid4().hex}.html"
    script = _container_visualization_script(
        container_output=container_output,
        dataset_key=resolved_dataset_key,
    )

    _run(
        [
            "docker",
            "exec",
            "-w",
            "/app",
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


def _resolve_dataset_key(
    *,
    run_dir: Path,
    run_id: str,
    dataset_key: str | None,
) -> str:
    if dataset_key:
        return dataset_key

    report_path = run_dir / "report.json"
    if report_path.exists():
        try:
            payload = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        if isinstance(payload, dict):
            raw_dataset_key = payload.get("dataset_key")
            if isinstance(raw_dataset_key, str) and raw_dataset_key.strip():
                return raw_dataset_key.strip()

    return f"tensorzero_cortex_{run_id}"


def _container_visualization_script(*, container_output: str, dataset_key: str) -> str:
    return f"""
import asyncio
import json
import sys

OUTPUT_PATH = {container_output!r}
DATASET_KEY = {dataset_key!r}


def _apply_cortex_runtime_config():
    from cortex_common import load_runtime_config, load_settings
    from cortex_knowledge.runtime import PythonCogneeRuntime, _resolved_cognee_config

    settings = load_settings()
    runtime_config = load_runtime_config(settings.runtime.path)
    PythonCogneeRuntime(config=_resolved_cognee_config(runtime_config))


async def _render_dataset_graph():
    _apply_cortex_runtime_config()

    from cognee.modules.users.methods import get_default_user
    from cognee.modules.data.methods import get_datasets, get_datasets_by_name
    from cognee.modules.visualization.cognee_network_visualization import (
        aggregate_multi_user_graphs,
        cognee_network_visualization,
    )

    user = await get_default_user()
    datasets = await get_datasets_by_name(DATASET_KEY, user.id)
    if not datasets:
        available = [dataset.name for dataset in await get_datasets(user.id)]
        raise RuntimeError(
            "Cognee dataset not found for visualization: "
            + DATASET_KEY
            + ". Available datasets: "
            + ", ".join(available[:20])
        )

    graph_data = await aggregate_multi_user_graphs([(user, datasets[0])])
    nodes, edges = graph_data
    if not nodes and not edges:
        raise RuntimeError(
            "Cognee graph has no nodes or edges for dataset "
            + DATASET_KEY
            + ". Check that the Knowledge Cognify job succeeded after the latest runtime config."
        )

    await cognee_network_visualization(graph_data, OUTPUT_PATH)
    print(
        json.dumps(
            {{
                "output_path": OUTPUT_PATH,
                "dataset_key": DATASET_KEY,
                "nodes": len(nodes),
                "edges": len(edges),
            }},
            ensure_ascii=False,
        )
    )


try:
    asyncio.run(_render_dataset_graph())
except Exception as exc:
    print(str(exc), file=sys.stderr)
    raise
"""


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
