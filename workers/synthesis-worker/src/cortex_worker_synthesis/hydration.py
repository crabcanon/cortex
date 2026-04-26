"""Input hydration for queued synthesis jobs."""

from __future__ import annotations

import csv
import io
from typing import Any

from cortex_common import NotFoundError, json_loads
from cortex_contracts import SynthesisJobSubmitRequest
from cortex_db import CortexUnitOfWork
from cortex_storage import StorageService


async def hydrate_synthesis_request(
    *,
    uow: CortexUnitOfWork,
    storage_service: StorageService | None,
    request: SynthesisJobSubmitRequest,
) -> SynthesisJobSubmitRequest:
    """Expand dataset/storage references into inline records or documents."""

    if request.source.inline_records or request.source.documents:
        return request

    records: list[dict[str, Any]] = []
    documents: list[str] = []
    if request.source.dataset_id:
        dataset_records, dataset_documents = await _dataset_payload(
            uow=uow,
            dataset_id=request.source.dataset_id,
        )
        records.extend(dataset_records)
        documents.extend(dataset_documents)

    object_ids = _object_ids(request.source.object_id, request.source.object_ids)
    if object_ids and storage_service is not None:
        for object_id in object_ids:
            record, payload = await storage_service.read_object_bytes(uow=uow, object_id=object_id)
            object_records, object_documents = _payload_from_bytes(
                payload,
                filename=record.filename,
                content_type=record.content_type,
            )
            records.extend(object_records)
            documents.extend(object_documents)

    if not records and not documents:
        return request

    hydrated_type = "inline_records" if records else "documents"
    hydrated_source = request.source.model_copy(
        update={
            "type": hydrated_type,
            "inline_records": records,
            "documents": documents,
        }
    )
    return request.model_copy(update={"source": hydrated_source})


async def _dataset_payload(
    *,
    uow: CortexUnitOfWork,
    dataset_id: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    dataset = await uow.datasets.get(dataset_id)
    if dataset is None:
        raise NotFoundError(f"Synthesis dataset `{dataset_id}` was not found.")
    items = await uow.dataset_items.list_for_dataset(dataset_id)
    records: list[dict[str, Any]] = []
    documents: list[str] = []
    for item in items:
        metadata = dict(item.metadata)
        if item.item_type in {"document", "doc"}:
            text = await _document_text(uow=uow, document_id=item.item_id)
            if text:
                documents.append(text)
            continue
        if metadata:
            records.append(_nested_record(metadata) or metadata)
    return records, documents


async def _document_text(*, uow: CortexUnitOfWork, document_id: str) -> str | None:
    document = await uow.documents.get(document_id)
    if document is None:
        return None
    if document.markdown:
        return document.markdown
    chunks = await uow.document_chunks.list_for_document(document_id)
    text = "\n\n".join(chunk.chunk_text for chunk in chunks if chunk.chunk_text)
    return text or None


def _object_ids(object_id: str | None, object_ids: list[str]) -> list[str]:
    unique: list[str] = []
    for candidate in [object_id, *object_ids]:
        if candidate and candidate not in unique:
            unique.append(candidate)
    return unique


def _payload_from_bytes(
    payload: bytes,
    *,
    filename: str,
    content_type: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    text = payload.decode("utf-8-sig")
    normalized_type = content_type.lower()
    normalized_name = filename.lower()
    if "jsonl" in normalized_type or normalized_name.endswith(".jsonl"):
        return (
            [
                record
                for line in text.splitlines()
                if line.strip()
                if isinstance((record := json_loads(line)), dict)
            ],
            [],
        )
    if "json" in normalized_type or normalized_name.endswith(".json"):
        return _payload_from_json(json_loads(text))
    if "csv" in normalized_type or normalized_name.endswith(".csv"):
        return [dict(row) for row in csv.DictReader(io.StringIO(text))], []
    return [], [text] if text.strip() else []


def _payload_from_json(payload: Any) -> tuple[list[dict[str, Any]], list[str]]:
    if isinstance(payload, list):
        if all(isinstance(item, str) for item in payload):
            return [], [str(item) for item in payload]
        return [record for record in payload if isinstance(record, dict)], []
    if isinstance(payload, dict):
        records = _nested_records(payload)
        if records:
            return records, []
        documents = _nested_documents(payload)
        if documents:
            return [], documents
        return [payload], []
    if isinstance(payload, str):
        return [], [payload]
    return [], []


def _nested_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("records", "items", "rows", "data", "test_cases", "goldens"):
        value = payload.get(key)
        if isinstance(value, list):
            return [record for record in value if isinstance(record, dict)]
    return []


def _nested_documents(payload: dict[str, Any]) -> list[str]:
    for key in ("documents", "contexts", "content", "text"):
        value = payload.get(key)
        if isinstance(value, list):
            return [str(item) for item in value if item is not None]
        if isinstance(value, str):
            return [value]
    return []


def _nested_record(payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("record", "item", "test_case", "golden"):
        value = payload.get(key)
        if isinstance(value, dict):
            return dict(value)
    return payload
