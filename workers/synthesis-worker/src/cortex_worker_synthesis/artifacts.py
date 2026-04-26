"""Synthesis artifact persistence helpers."""

from __future__ import annotations

from dataclasses import dataclass

from cortex_common import json_dumps
from cortex_contracts import StoredArtifactRef, SynthesisJobSubmitRequest, SynthesisRunResult
from cortex_db import CortexUnitOfWork
from cortex_storage import StorageService


@dataclass(slots=True)
class WorkerStorageCaller:
    tenant_id: str
    subject: str
    actor_id: str | None = None


async def persist_synthesis_output(
    *,
    uow: CortexUnitOfWork,
    storage_service: StorageService | None,
    caller: WorkerStorageCaller,
    request: SynthesisJobSubmitRequest,
    result: SynthesisRunResult,
) -> SynthesisRunResult:
    if storage_service is None:
        return result
    if any(output.label == "synthesis_output" for output in result.outputs):
        return result

    filename = (
        request.output.persist_object_filename
        or f"{result.synthesis_run_id or result.job_id or 'synthesis'}-output.json"
    )
    payload = json_dumps(result.model_dump(mode="json")).encode("utf-8")
    stored = await storage_service.upload_small_file(
        uow=uow,
        caller=caller,
        filename=filename,
        content=payload,
        content_type="application/json",
        metadata={
            "cortex.artifact.kind": "synthesis_output",
            "cortex.job_id": result.job_id or "",
            "cortex.synthesis_run_id": result.synthesis_run_id or "",
        },
        tags=["synthesis", "output"],
    )
    outputs = [
        *result.outputs,
        StoredArtifactRef(
            object_id=stored.object_id,
            label="synthesis_output",
            content_type=stored.content_type,
            format=request.output.output_format or "json",
            description="Canonical Cortex synthesis output.",
        ),
    ]
    return result.model_copy(update={"outputs": outputs})
