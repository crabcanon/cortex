from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx


class CortexApiError(RuntimeError):
    def __init__(self, method: str, path: str, response: httpx.Response) -> None:
        detail = response.text
        try:
            parsed = response.json()
            detail = parsed.get("detail") or parsed.get("title") or json.dumps(parsed)
        except ValueError:
            pass
        super().__init__(f"{method} {path} failed with {response.status_code}: {detail}")
        self.response = response


class CortexClient:
    def __init__(
        self,
        *,
        base_url: str,
        tenant_id: str,
        actor_id: str,
        bearer_token: str | None,
        timeout_seconds: float,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.tenant_id = tenant_id
        self.actor_id = actor_id
        self._token = bearer_token
        self._client = httpx.Client(timeout=timeout_seconds, trust_env=False)

    def close(self) -> None:
        self._client.close()

    def ensure_token(self) -> str:
        if self._token:
            return self._token
        payload = {
            "subject": self.actor_id,
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
            "actor_type": "service",
            "display_name": "TensorZero Cortex Example",
            "scopes": [
                "health:read",
                "parse:read",
                "parse:write",
                "storage:read",
                "storage:write",
                "knowledge:read",
                "knowledge:write",
                "eval:read",
                "eval:write",
                "jobs:read",
                "jobs:cancel",
            ],
            "roles": ["tenant_admin"],
            "groups": ["examples"],
            "expires_in": 86400,
            "additional_claims": {"example": "tensorzero-cortex"},
        }
        data = self.post("/v1/dev/auth/token", json_body=payload, auth=False)
        self._token = data["access_token"]
        return self._token

    def parse_sync(
        self,
        *,
        sources: list[str],
        engine_id: str,
        scene: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"sources": sources, "engine_id": engine_id}
        if scene:
            payload["scene"] = scene
        return self.post("/v1/parse/sync", json_body=payload)

    def parse_async(
        self,
        *,
        sources: list[str],
        engine_id: str,
        scene: str | None = None,
        priority: int = 5,
        timeout_seconds: int = 900,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "sources": sources,
            "engine_id": engine_id,
            "priority": priority,
        }
        if scene:
            payload["scene"] = scene
        accepted = self.post("/v1/parse/jobs", json_body=payload)
        jobs = accepted.get("jobs") or []
        results: list[dict[str, Any]] = []
        job_statuses: list[dict[str, Any]] = []
        for job in jobs:
            job_id = str(job["job_id"])
            job_statuses.append(self.wait_job(job_id, timeout_seconds=timeout_seconds))
            job_result = self.wait_parse_result(job_id, timeout_seconds=timeout_seconds)
            results.extend(job_result.get("results") or [])
        return {
            "requested_sources": accepted.get("requested_sources") or sources,
            "engine_id": accepted.get("engine_id") or engine_id,
            "scene": accepted.get("scene"),
            "jobs": jobs,
            "job_statuses": job_statuses,
            "results": results,
        }

    def wait_parse_result(self, job_id: str, *, timeout_seconds: int = 900) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        last_status: dict[str, Any] = {}
        while time.monotonic() < deadline:
            response = self._client.get(
                f"{self.base_url}/v1/parse/jobs/{job_id}/result",
                headers={"Authorization": f"Bearer {self.ensure_token()}"},
            )
            if response.status_code == 200:
                return response.json()
            if response.status_code == 409:
                last_status = response.json()
                time.sleep(3)
                continue
            if response.status_code >= 400:
                raise CortexApiError("GET", f"/v1/parse/jobs/{job_id}/result", response)
        raise TimeoutError(
            f"Timed out waiting for parse result {job_id}. Last status: {last_status}"
        )

    def upload_markdown(
        self,
        *,
        filename: str,
        markdown: str,
        metadata: dict[str, Any],
        tags: list[str],
    ) -> dict[str, Any]:
        files = {
            "file": (
                filename,
                markdown.encode("utf-8"),
                "text/markdown",
            )
        }
        data = {
            "metadata_json": json.dumps(metadata, ensure_ascii=False),
            "access_policy_json": json.dumps({"access_level": "tenant_shared"}),
            "tags": ",".join(tags),
        }
        return self.request("POST", "/v1/storage/files", data=data, files=files)

    def create_dataset(
        self,
        *,
        dataset_key: str,
        display_name: str,
        description: str,
    ) -> dict[str, Any]:
        payload = {
            "dataset_key": dataset_key,
            "display_name": display_name,
            "description": description,
            "tags": ["tensorzero", "cortex", "finance", "ab-test"],
            "retention_class": "temporary",
            "metadata": {"example": "tensorzero-cortex"},
            "access_policy": {
                "access_level": "tenant_shared",
                "classification_labels": ["internal"],
                "allowed_role_keys": ["tenant_admin", "analyst"],
                "denied_role_keys": [],
                "purpose_tags": ["search", "evaluation", "ab_test"],
                "constraints": {},
            },
        }
        return self.post("/v1/knowledge/datasets", json_body=payload)

    def add_objects_to_knowledge(
        self,
        *,
        dataset_key: str,
        object_ids: list[str],
    ) -> dict[str, Any]:
        inputs = [
            {
                "input_type": "object_id",
                "object_id": object_id,
                "label": f"Parsed Markdown {object_id}",
                "node_set": ["tensorzero", "finance", "parsed_markdown"],
                "metadata": {"source": "storage", "example": "tensorzero-cortex"},
            }
            for object_id in object_ids
        ]
        payload = {
            "dataset_key": dataset_key,
            "inputs": inputs,
            "options": {
                "normalize_text": True,
                "structured_ingest": True,
                "incremental": True,
                "persist_source_copy": True,
            },
        }
        return self.post("/v1/knowledge/add/jobs", json_body=payload)

    def cognify(self, *, dataset_key: str) -> dict[str, Any]:
        payload = {
            "dataset_key": dataset_key,
            "incremental_loading": True,
            "graph_prompt_profile": "simple",
            "chunking": {
                "enabled": True,
                "strategy": "semantic",
                "target_tokens": 512,
                "overlap_tokens": 64,
                "max_chunks": 512,
            },
        }
        return self.post("/v1/knowledge/cognify/jobs", json_body=payload)

    def search_knowledge(
        self,
        *,
        dataset_key: str,
        query: str,
        search_type: str,
        top_k: int = 8,
    ) -> dict[str, Any]:
        payload = {
            "query_text": query,
            "dataset_keys": [dataset_key],
            "search_type": search_type,
            "top_k": top_k,
            "filters": {
                "document_ids": [],
                "object_ids": [],
                "tags": [],
                "node_sets": ["tensorzero", "finance", "parsed_markdown"],
                "metadata": {},
            },
            "only_context": False,
            "include_provenance": True,
            "include_graph_paths": True,
            "timeout_seconds": 60,
        }
        return self.post("/v1/knowledge/search", json_body=payload)

    def run_eval_sync(self, *, name: str, test_cases: list[dict[str, Any]]) -> dict[str, Any]:
        return self.post(
            "/v1/eval/sync",
            json_body=self._eval_payload(name=name, test_cases=test_cases),
        )

    def run_eval_async(
        self,
        *,
        name: str,
        test_cases: list[dict[str, Any]],
        timeout_seconds: int = 1200,
    ) -> dict[str, Any]:
        accepted = self.post(
            "/v1/eval/jobs",
            json_body=self._eval_payload(name=name, test_cases=test_cases),
        )
        job_id = str(accepted["job_id"])
        job = self.wait_job(job_id, timeout_seconds=timeout_seconds)
        result = self.wait_eval_result(job_id, timeout_seconds=timeout_seconds)
        return {
            "mode": "async",
            "job_id": job_id,
            "accepted": accepted,
            "job": job,
            "result": result,
        }

    def wait_eval_result(self, job_id: str, *, timeout_seconds: int = 1200) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        last_status: dict[str, Any] = {}
        while time.monotonic() < deadline:
            response = self._client.get(
                f"{self.base_url}/v1/eval/jobs/{job_id}/result",
                headers={"Authorization": f"Bearer {self.ensure_token()}"},
            )
            if response.status_code == 200:
                return response.json()
            if response.status_code == 409:
                last_status = response.json()
                time.sleep(3)
                continue
            if response.status_code >= 400:
                raise CortexApiError("GET", f"/v1/eval/jobs/{job_id}/result", response)
        raise TimeoutError(
            f"Timed out waiting for evaluation result {job_id}. Last status: {last_status}"
        )

    @staticmethod
    def _eval_payload(*, name: str, test_cases: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "name": name,
            "eval_type": "rag",
            "engine_id": "deepeval",
            "input": {"type": "inline_test_cases", "test_cases": test_cases},
            "target": {"type": "existing_outputs"},
            "metrics": [
                {"metric_key": "rag.answer_relevancy", "threshold": 0.65, "weight": 0.4},
                {"metric_key": "rag.faithfulness", "threshold": 0.65, "weight": 0.4},
                {"metric_key": "rag.contextual_relevancy", "threshold": 0.6, "weight": 0.2},
            ],
            "output": {
                "persist_report_object": True,
                "include_sample_results": True,
                "max_failures_reported": 20,
            },
        }

    def wait_job(self, job_id: str, *, timeout_seconds: int = 600) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        last_status: dict[str, Any] = {}
        while time.monotonic() < deadline:
            last_status = self.get(f"/v1/jobs/{job_id}")
            status = str(last_status.get("status", "")).lower()
            if status in {"succeeded", "failed", "cancelled", "canceled", "timed_out"}:
                if status != "succeeded":
                    raise RuntimeError(f"Job {job_id} ended as {status}: {last_status}")
                return last_status
            time.sleep(3)
        raise TimeoutError(f"Timed out waiting for job {job_id}. Last status: {last_status}")

    def get(self, path: str) -> dict[str, Any]:
        return self.request("GET", path)

    def post(self, path: str, *, json_body: dict[str, Any], auth: bool = True) -> dict[str, Any]:
        return self.request("POST", path, json=json_body, auth=auth)

    def request(
        self,
        method: str,
        path: str,
        *,
        auth: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any]:
        headers = dict(kwargs.pop("headers", {}) or {})
        if auth:
            headers["Authorization"] = f"Bearer {self.ensure_token()}"
        response = self._client.request(method, f"{self.base_url}{path}", headers=headers, **kwargs)
        if response.status_code >= 400:
            raise CortexApiError(method, path, response)
        if not response.content:
            return {}
        return response.json()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
