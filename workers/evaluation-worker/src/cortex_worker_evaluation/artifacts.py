"""Evaluation artifact persistence helpers."""

from __future__ import annotations

from dataclasses import dataclass

from cortex_common import json_dumps
from cortex_contracts import EvalJobSubmitRequest, EvalRunResult, StoredArtifactRef
from cortex_db import CortexUnitOfWork
from cortex_storage import StorageService


@dataclass(slots=True)
class WorkerStorageCaller:
    tenant_id: str
    subject: str
    actor_id: str | None = None


async def persist_evaluation_report(
    *,
    uow: CortexUnitOfWork,
    storage_service: StorageService | None,
    caller: WorkerStorageCaller,
    request: EvalJobSubmitRequest,
    result: EvalRunResult,
) -> EvalRunResult:
    if storage_service is None or not request.output.persist_report_object:
        return result
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
        },
        tags=["evaluation", "report"],
    )
    artifacts = [
        *result.artifacts,
        StoredArtifactRef(
            object_id=stored.object_id,
            label="evaluation_report",
            content_type=stored.content_type,
            format="json",
            description="Canonical Cortex evaluation report.",
        ),
    ]
    return result.model_copy(update={"artifacts": artifacts})
