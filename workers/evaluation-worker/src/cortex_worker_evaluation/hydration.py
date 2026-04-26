"""Input hydration for queued evaluation jobs."""

from __future__ import annotations

import csv
import io
from typing import Any

from cortex_common import NotFoundError, json_loads
from cortex_contracts import (
    EvalConversationTurn,
    EvalFieldMapping,
    EvalJobSubmitRequest,
    EvalTestCase,
)
from cortex_db import CortexUnitOfWork
from cortex_storage import StorageService


async def hydrate_evaluation_request(
    *,
    uow: CortexUnitOfWork,
    storage_service: StorageService | None,
    request: EvalJobSubmitRequest,
) -> EvalJobSubmitRequest:
    """Expand dataset/storage references into inline eval cases when possible."""

    if request.input.test_cases:
        return request

    records: list[dict[str, Any]] = []
    if request.input.dataset_id:
        records.extend(await _dataset_records(uow=uow, dataset_id=request.input.dataset_id))

    object_ids = _object_ids(request.input.object_id, request.input.object_ids)
    if object_ids and storage_service is not None:
        for object_id in object_ids:
            record, payload = await storage_service.read_object_bytes(uow=uow, object_id=object_id)
            records.extend(
                _records_from_bytes(
                    payload,
                    filename=record.filename,
                    content_type=record.content_type,
                )
            )

    test_cases = [
        _case
        for record in records
        if (_case := _test_case_from_record(record, request.input.field_mapping))
    ]
    if not test_cases:
        return request

    hydrated_input = request.input.model_copy(
        update={
            "type": "inline_test_cases",
            "test_cases": test_cases,
        }
    )
    return request.model_copy(update={"input": hydrated_input})


async def _dataset_records(*, uow: CortexUnitOfWork, dataset_id: str) -> list[dict[str, Any]]:
    dataset = await uow.datasets.get(dataset_id)
    if dataset is None:
        raise NotFoundError(f"Evaluation dataset `{dataset_id}` was not found.")
    items = await uow.dataset_items.list_for_dataset(dataset_id)
    records: list[dict[str, Any]] = []
    for item in items:
        metadata = dict(item.metadata)
        if not metadata:
            continue
        candidate = _nested_record(metadata) or metadata
        candidate.setdefault("_dataset_item_type", item.item_type)
        candidate.setdefault("_dataset_item_id", item.item_id)
        if item.label:
            candidate.setdefault("_label", item.label)
        records.append(candidate)
    return records


def _object_ids(object_id: str | None, object_ids: list[str]) -> list[str]:
    unique: list[str] = []
    for candidate in [object_id, *object_ids]:
        if candidate and candidate not in unique:
            unique.append(candidate)
    return unique


def _records_from_bytes(
    payload: bytes,
    *,
    filename: str,
    content_type: str,
) -> list[dict[str, Any]]:
    text = payload.decode("utf-8-sig")
    normalized_type = content_type.lower()
    normalized_name = filename.lower()
    if "jsonl" in normalized_type or normalized_name.endswith(".jsonl"):
        return [
            record
            for line in text.splitlines()
            if line.strip()
            if isinstance((record := json_loads(line)), dict)
        ]
    if "json" in normalized_type or normalized_name.endswith(".json"):
        return _records_from_json_payload(json_loads(text))
    if "csv" in normalized_type or normalized_name.endswith(".csv"):
        return [dict(row) for row in csv.DictReader(io.StringIO(text))]
    return [{"text": text, "content": text}] if text.strip() else []


def _records_from_json_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [record for record in payload if isinstance(record, dict)]
    if isinstance(payload, dict):
        nested = _nested_records(payload)
        return nested if nested else [payload]
    return []


def _nested_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("test_cases", "records", "items", "rows", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return [record for record in value if isinstance(record, dict)]
    return []


def _nested_record(payload: dict[str, Any]) -> dict[str, Any] | None:
    for key in ("test_case", "record", "item"):
        value = payload.get(key)
        if isinstance(value, dict):
            return dict(value)
    return None


def _test_case_from_record(
    record: dict[str, Any],
    mapping: EvalFieldMapping | None,
) -> EvalTestCase | None:
    effective_mapping = mapping or EvalFieldMapping()
    user_input = _string_field(
        record,
        effective_mapping.user_input,
        "user_input",
        "input",
        "question",
        "prompt",
        "query",
    )
    actual_output = _string_field(
        record,
        effective_mapping.actual_output,
        "actual_output",
        "answer",
        "output",
        "response",
        "prediction",
    )
    expected_output = _string_field(
        record,
        effective_mapping.expected_output,
        "expected_output",
        "expected",
        "ground_truth",
        "reference",
    )
    retrieval_contexts = _list_field(
        record,
        effective_mapping.retrieval_contexts,
        "retrieval_contexts",
        "retrieval_context",
        "contexts",
        "context",
    )
    conversation_turns = _conversation_turns(
        _raw_field(
            record,
            effective_mapping.conversation_turns,
            "conversation_turns",
            "turns",
            "messages",
        )
    )
    has_content = any(
        [user_input, actual_output, expected_output, retrieval_contexts, conversation_turns]
    )
    if not has_content:
        return None
    return EvalTestCase(
        user_input=user_input,
        actual_output=actual_output,
        expected_output=expected_output,
        retrieval_contexts=retrieval_contexts,
        conversation_turns=conversation_turns,
        metadata={
            key: value
            for key, value in record.items()
            if key.startswith("_") or key not in {"user_input", "actual_output", "expected_output"}
        },
    )


def _raw_field(record: dict[str, Any], *names: str | None) -> Any:
    for name in names:
        if name and name in record:
            return record[name]
    return None


def _string_field(record: dict[str, Any], *names: str | None) -> str | None:
    value = _raw_field(record, *names)
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _list_field(record: dict[str, Any], *names: str | None) -> list[str]:
    value = _raw_field(record, *names)
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    if isinstance(value, tuple):
        return [str(item) for item in value if item is not None]
    return [str(value)]


def _conversation_turns(value: Any) -> list[EvalConversationTurn]:
    if not isinstance(value, list):
        return []
    turns: list[EvalConversationTurn] = []
    for item in value:
        if isinstance(item, EvalConversationTurn):
            turns.append(item)
        elif isinstance(item, dict):
            try:
                turns.append(EvalConversationTurn.model_validate(item))
            except ValueError:
                continue
    return turns
