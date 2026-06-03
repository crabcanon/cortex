"""Evaluation artifact persistence helpers."""

from __future__ import annotations

import asyncio
import mimetypes
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cortex_common import json_dumps
from cortex_contracts import EvalRunResult, EvalSyncRequest, EvalType, StoredArtifactRef
from cortex_db import CortexUnitOfWork


@dataclass(slots=True)
class EvaluationStorageCaller:
    tenant_id: str
    subject: str
    actor_id: str | None = None


async def persist_evaluation_report(
    *,
    uow: CortexUnitOfWork,
    storage_service: Any | None,
    caller: EvaluationStorageCaller,
    request: EvalSyncRequest,
    result: EvalRunResult,
) -> EvalRunResult:
    if storage_service is None or not request.output.persist_report_object:
        return result
    result = await _persist_evalscope_native_artifacts(
        uow=uow,
        storage_service=storage_service,
        caller=caller,
        request=request,
        result=result,
    )
    if any(artifact.label == "evaluation_report" for artifact in result.artifacts):
        return result

    filename = f"{result.eval_run_id or result.job_id or 'evaluation'}-report.json"
    payload = json_dumps(result.model_dump(mode="json")).encode("utf-8")
    stored = await storage_service.upload_small_file(
        uow=uow,
        caller=caller,
        filename=filename,
        content=payload,
        content_type="application/json",
        metadata={
            "cortex.artifact.kind": "evaluation_report",
            "cortex.job_id": result.job_id or "",
            "cortex.eval_run_id": result.eval_run_id or "",
            "cortex.eval_type": result.eval_type.value,
            "cortex.engine_id": result.engine_id,
        },
        tags=["evaluation", "report"],
    )
    artifacts = [
        *result.artifacts,
        StoredArtifactRef(
            object_id=stored.object_id,
            label="evaluation_report",
            uri=_artifact_uri(stored),
            content_type=stored.content_type,
            format="json",
            description="Canonical Cortex evaluation report.",
        ),
    ]
    return result.model_copy(update={"artifacts": artifacts})


async def _persist_evalscope_native_artifacts(
    *,
    uow: CortexUnitOfWork,
    storage_service: Any,
    caller: EvaluationStorageCaller,
    request: EvalSyncRequest,
    result: EvalRunResult,
) -> EvalRunResult:
    if result.engine_id != "evalscope":
        return result
    artifact_dir = _evalscope_artifact_dir(request=request, result=result)
    if artifact_dir is None or not artifact_dir.is_dir():
        return result
    files = sorted(path for path in artifact_dir.rglob("*") if path.is_file())
    if not files:
        await _remove_directory(artifact_dir)
        return result

    artifacts = list(result.artifacts)
    object_key_prefix = "/".join(
        [
            "evaluation",
            result.job_id or result.eval_run_id or "unknown",
            "evalscope",
            artifact_dir.name,
        ]
    )
    for path in files:
        relative_path = path.relative_to(artifact_dir).as_posix()
        content = await asyncio.to_thread(path.read_bytes)
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        stored = await storage_service.upload_artifact_file(
            uow=uow,
            caller=caller,
            filename=path.name,
            content=content,
            object_key_prefix=object_key_prefix,
            relative_path=relative_path,
            content_type=content_type,
            metadata={
                "cortex.artifact.kind": "evalscope_native_artifact",
                "cortex.artifact.relative_path": relative_path,
                "cortex.job_id": result.job_id or "",
                "cortex.eval_run_id": result.eval_run_id or "",
                "cortex.eval_type": result.eval_type.value,
                "cortex.engine_id": result.engine_id,
            },
            tags=["evaluation", "evalscope", "artifact"],
        )
        artifacts.append(
            StoredArtifactRef(
                object_id=stored.object_id,
                label="evalscope_artifact",
                uri=_artifact_uri(stored),
                content_type=stored.content_type,
                format=_artifact_format(path),
                description=f"EvalScope native artifact: {relative_path}",
            )
        )
    await _remove_directory(artifact_dir)
    return result.model_copy(update={"artifacts": artifacts})


def _evalscope_artifact_dir(
    *,
    request: EvalSyncRequest,
    result: EvalRunResult,
) -> Path | None:
    task_id = _evalscope_task_id(request=request, result=result)
    if not task_id:
        return None
    root = Path(os.getenv("CORTEX_EVALSCOPE_OUTPUT_ROOT", "/app/outputs"))
    subdir = "perf" if request.eval_type is EvalType.PERF else "eval"
    return root / task_id / subdir


def _evalscope_task_id(
    *,
    request: EvalSyncRequest,
    result: EvalRunResult,
) -> str | None:
    for key in ("evalscope_task_id", "task_id", "cortex_job_id", "job_id"):
        value = request.engine_options.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return result.job_id or result.eval_run_id


async def _remove_directory(path: Path) -> None:
    root = Path(os.getenv("CORTEX_EVALSCOPE_OUTPUT_ROOT", "/app/outputs")).resolve()
    target = path.resolve()
    if root == target or root not in target.parents:
        return
    await asyncio.to_thread(shutil.rmtree, target, True)


def _artifact_format(path: Path) -> str | None:
    suffix = path.suffix.lstrip(".").lower()
    return suffix or None


def _artifact_uri(stored: Any) -> str | None:
    if getattr(stored, "bucket", None) and getattr(stored, "object_key", None):
        return f"s3://{stored.bucket}/{stored.object_key}"
    return None
