"""EvalScope evaluation engines."""

from __future__ import annotations

import asyncio
import importlib
import threading
import time
from typing import Any

import httpx
from cortex_common import CortexError, new_prefixed_id, utc_now
from cortex_contracts import (
    EvalEngineDescriptor,
    EvalRunResult,
    EvalSyncRequest,
    EvalType,
)

from .utils.evalscope_cleaner import _normalize_evalscope_result

_EVALSCOPE_HEADER_ONLY_OPTION_KEYS = frozenset(
    {
        "evalscope_task_id",
        "task_id",
        "cortex_job_id",
        "job_id",
    }
)
_SHORT_PROMPT_DATASET_MAX_RECOMMENDED_MIN_TOKENS = {
    "openqa": 256,
}


class EvalScopeEvaluationEngine:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        headers: dict[str, str],
        availability_status: str = "available",
        display_name: str = "EvalScope",
        notes: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._headers = dict(headers)
        self._descriptor = EvalEngineDescriptor(
            engine_id="evalscope",
            display_name=display_name,
            provider="Alibaba Cloud / OSS",
            availability_status=availability_status,
            execution_modes=["sync", "async"],
            supported_eval_types=[EvalType.PERF, EvalType.RAG, EvalType.CUSTOM],
            supported_metric_prefixes=["perf", "rag", "quality"],
            default_profiles=["perf_default", "service_eval_default"],
            notes=notes,
        )

    @property
    def descriptor(self) -> EvalEngineDescriptor:
        return self._descriptor

    async def run(self, request: EvalSyncRequest) -> EvalRunResult:
        endpoint = _evalscope_invoke_endpoint(request.eval_type)
        payload = _build_evalscope_payload(request)
        headers = _evalscope_request_headers(self._headers, request)
        started_at = utc_now()
        async with httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            headers=headers,
        ) as client:
            response = await client.post(endpoint, json=payload)
        if response.status_code >= 400:
            message = (
                f"EvalScope request failed with status {response.status_code}: {response.text}"
            )
            raise CortexError(
                code="evalscope_request_failed",
                detail=message,
                status_code=502,
            )
        return _normalize_evalscope_result(request, response.json(), started_at)


class EvalScopeSelfHostedSdkEvaluationEngine(EvalScopeEvaluationEngine):
    """Launch the EvalScope service from the Python SDK and call its REST API."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        timeout_seconds: float,
        headers: dict[str, str],
        debug: bool,
        startup_timeout_seconds: float,
        available: bool,
        local_available: bool | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._debug = debug
        self._startup_timeout_seconds = startup_timeout_seconds
        self._local_available = available if local_available is None else local_available
        self._service_thread: threading.Thread | None = None
        self._service_error: Exception | None = None
        self._service_started = False
        self._startup_lock = asyncio.Lock()
        status = (
            "available"
            if available and self._local_available
            else "degraded"
            if available
            else "disabled"
        )
        notes = (
            None
            if status == "available"
            else (
                "EvalScope self-hosted SDK mode is enabled and routable to runtime workers, "
                "but `evalscope[service]` is not installed in this process."
            )
            if status == "degraded"
            else "Enable EvalScope in runtime config and install `evalscope[service]`."
        )
        super().__init__(
            base_url=f"http://{host}:{port}",
            timeout_seconds=timeout_seconds,
            headers=headers,
            availability_status=status,
            display_name="EvalScope (Self-hosted SDK)",
            notes=notes,
        )

    async def run(self, request: EvalSyncRequest) -> EvalRunResult:
        if self.descriptor.availability_status == "disabled":
            raise CortexError(
                code="evalscope_runtime_not_available",
                detail="EvalScope is disabled for this deployment.",
                status_code=503,
            )
        if not self._local_available:
            raise CortexError(
                code="evalscope_sdk_runtime_not_available_in_process",
                detail=(
                    "EvalScope self-hosted SDK mode is enabled for async routing, but "
                    "`evalscope[service]` is not installed in this process. Use "
                    "`cortex-evaluation-worker-runtime`, or install "
                    "`cortex-evaluation[evalscope]` in the API process for `/v1/eval/sync`."
                ),
                status_code=503,
            )
        await self._ensure_service_started()
        return await super().run(request)

    async def _ensure_service_started(self) -> None:
        if self._service_started and await self._probe_health():
            return
        async with self._startup_lock:
            if self._service_started and await self._probe_health():
                return
            if await self._probe_health():
                self._service_started = True
                return
            if self._service_thread is None or not self._service_thread.is_alive():
                self._service_error = None
                self._service_thread = threading.Thread(
                    target=self._run_service,
                    name=f"evalscope-service-{self._port}",
                    daemon=True,
                )
                self._service_thread.start()
            deadline = time.monotonic() + self._startup_timeout_seconds
            while time.monotonic() < deadline:
                if self._service_error is not None:
                    raise CortexError(
                        code="evalscope_service_start_failed",
                        detail=f"Failed to start EvalScope service: {self._service_error}",
                        status_code=503,
                    )
                if await self._probe_health():
                    self._service_started = True
                    return
                await asyncio.sleep(0.5)
            raise CortexError(
                code="evalscope_service_start_timeout",
                detail=(
                    "EvalScope self-hosted service did not become healthy before the startup "
                    f"timeout of {self._startup_timeout_seconds} seconds."
                ),
                status_code=503,
            )

    def _run_service(self) -> None:
        try:
            module = importlib.import_module("evalscope.service")
            module.run_service(host=self._host, port=self._port, debug=self._debug)
        except Exception as exc:  # pragma: no cover - depends on third-party server runtime
            self._service_error = exc

    async def _probe_health(self) -> bool:
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=min(self._timeout, 5.0),
                headers=self._headers,
            ) as client:
                response = await client.get("/health")
            return 200 <= response.status_code < 300
        except Exception:
            return False


def _build_evalscope_payload(request: EvalSyncRequest) -> dict[str, Any]:
    payload = {
        key: value
        for key, value in request.engine_options.items()
        if key not in _EVALSCOPE_HEADER_ONLY_OPTION_KEYS
    }
    if request.target is not None:
        if request.target.headers and "headers" not in payload:
            payload["headers"] = dict(request.target.headers)
        if request.target.request_template and "request_template" not in payload:
            payload["request_template"] = dict(request.target.request_template)
        if request.target.provider and "provider" not in payload:
            payload["provider"] = request.target.provider
        if (
            request.eval_type is EvalType.PERF
            and request.target.endpoint_url
            and "url" not in payload
        ):
            payload["url"] = request.target.endpoint_url
        elif request.target.endpoint_url and "api_url" not in payload:
            payload["api_url"] = request.target.endpoint_url
        if request.target.model_ref and "model" not in payload:
            payload["model"] = request.target.model_ref
        if request.eval_type is EvalType.PERF:
            if request.target.protocol and "api" not in payload:
                payload["api"] = _evalscope_api_protocol(request.target.protocol)
            elif "api" not in payload:
                payload["api"] = "openai"
            if request.target.api_key and "api_key" not in payload:
                payload["api_key"] = request.target.api_key
            headers = dict(payload.get("headers") or {})
            _apply_target_api_key_header(headers, request.target)
            if headers:
                payload["headers"] = headers
    if (
        request.eval_type is not EvalType.PERF
        and request.input.builtin_dataset_key
        and "datasets" not in payload
    ):
        payload["datasets"] = [request.input.builtin_dataset_key]
    if request.input.builtin_dataset_key and "dataset" not in payload:
        payload["dataset"] = request.input.builtin_dataset_key
    if request.metrics and "metrics" not in payload:
        payload["metrics"] = [metric.metric_key for metric in request.metrics]
    _validate_evalscope_perf_payload(request, payload)
    return payload


def _evalscope_invoke_endpoint(eval_type: EvalType) -> str:
    if eval_type is EvalType.PERF:
        return "/api/v1/perf/invoke"
    return "/api/v1/eval/invoke"


def _evalscope_request_headers(
    base_headers: dict[str, str],
    request: EvalSyncRequest,
) -> dict[str, str]:
    headers = dict(base_headers)
    if any(key.lower() == "evalscope-task-id" for key in headers):
        return headers
    headers["EvalScope-Task-Id"] = _evalscope_task_id(request)
    return headers


def _evalscope_task_id(request: EvalSyncRequest) -> str:
    for key in ("evalscope_task_id", "task_id", "cortex_job_id", "job_id"):
        value = request.engine_options.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return new_prefixed_id("evalscope_task")


def _evalscope_api_protocol(protocol: str) -> str:
    normalized = protocol.strip().lower().replace("-", "_")
    if normalized in {"openai_compatible", "openai"}:
        return "openai"
    return normalized


def _apply_target_api_key_header(headers: dict[str, str], target: Any) -> None:
    if not target.api_key:
        return
    header_name = target.api_key_header or "Authorization"
    if any(existing.lower() == header_name.lower() for existing in headers):
        return
    prefix = (target.api_key_prefix or "").strip()
    headers[header_name] = f"{prefix} {target.api_key}".strip()


def _validate_evalscope_perf_payload(
    request: EvalSyncRequest,
    payload: dict[str, Any],
) -> None:
    if request.eval_type is not EvalType.PERF:
        return
    dataset = str(payload.get("dataset") or "").strip().lower()
    if not dataset:
        return
    if payload.get("prompt") or payload.get("dataset_path"):
        return
    min_prompt_length = _coerce_int(payload.get("min_prompt_length"))
    if min_prompt_length is None:
        return
    max_recommended = _SHORT_PROMPT_DATASET_MAX_RECOMMENDED_MIN_TOKENS.get(dataset)
    if max_recommended is None or min_prompt_length <= max_recommended:
        return
    raise CortexError(
        code="evalscope_dataset_filter_too_strict",
        detail=(
            f"EvalScope dataset `{dataset}` is a short-prompt dataset; "
            f"`min_prompt_length={min_prompt_length}` can filter out every sample before "
            "the benchmark starts. Remove `min_prompt_length`, set it to 0, provide "
            "`engine_options.prompt` / `engine_options.dataset_path`, or choose a long-prompt "
            "dataset such as `longalpaca`."
        ),
        status_code=422,
    )


def _coerce_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lstrip("-").isdigit():
            return int(stripped)
    return None
