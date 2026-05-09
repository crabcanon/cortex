from __future__ import annotations

import json
import time
from typing import Any

import httpx


class TensorZeroError(RuntimeError):
    pass


class TensorZeroClient:
    def __init__(self, *, gateway_url: str, timeout_seconds: float) -> None:
        self.gateway_url = gateway_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._client = httpx.Client(timeout=timeout_seconds, trust_env=False)

    def close(self) -> None:
        self._client.close()

    def status(
        self,
        *,
        timeout_seconds: float = 180,
        delay_seconds: float = 2.0,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        last_error: str | None = None
        attempts = 0
        while time.monotonic() < deadline:
            attempts += 1
            try:
                response = self._client.get(f"{self.gateway_url}/status")
                if response.status_code < 500:
                    if response.status_code >= 400:
                        raise TensorZeroError(
                            "TensorZero Gateway status check failed: "
                            f"{response.status_code} {response.text}"
                        )
                    return response.json()
                last_error = f"{response.status_code} {response.text}"
            except httpx.HTTPError as exc:
                last_error = str(exc)
            time.sleep(delay_seconds)
        raise TensorZeroError(
            "TensorZero Gateway is not ready after "
            f"{attempts} attempts over {timeout_seconds:.0f}s at "
            f"{self.gateway_url}/status. Last error: {last_error}"
        )

    def inference(
        self,
        *,
        question: str,
        context: str,
        metadata: dict[str, Any],
        variant_name: str | None = None,
        include_raw_response: bool = False,
    ) -> dict[str, Any]:
        user_content = (
            "Question:\n"
            f"{question}\n\n"
            "Cortex Knowledge context:\n"
            f"{context}\n\n"
            "Metadata:\n"
            f"{json.dumps(metadata, ensure_ascii=False)}"
        )
        payload: dict[str, Any] = {
            "function_name": "cortex_rag_answer",
            "input": {"messages": [{"role": "user", "content": user_content}]},
        }
        if variant_name:
            payload["variant_name"] = variant_name
        if include_raw_response:
            payload["include_original_response"] = True
        try:
            response = self._client.post(f"{self.gateway_url}/inference", json=payload)
        except httpx.TimeoutException as exc:
            variant = variant_name or "adaptive"
            raise TensorZeroError(
                "TensorZero inference timed out after "
                f"{self.timeout_seconds:.0f}s for variant `{variant}` at "
                f"{self.gateway_url}/inference. If this is a local Ollama run, "
                "verify the Gateway container can reach OLLAMA_BASE_URL, reduce "
                "TENSORZERO_MAX_CONTEXT_CHARS_PER_GROUP / TENSORZERO_OLLAMA_MAX_TOKENS, "
                "or increase REQUEST_TIMEOUT_SECONDS."
            ) from exc
        except httpx.RequestError as exc:
            variant = variant_name or "adaptive"
            raise TensorZeroError(
                f"TensorZero inference request failed for variant `{variant}` at "
                f"{self.gateway_url}/inference: {exc}"
            ) from exc
        if response.status_code >= 400:
            raise TensorZeroError(
                f"TensorZero inference failed: {response.status_code} {response.text}"
            )
        data = response.json()
        return {
            "raw": data,
            "inference_id": data.get("inference_id"),
            "episode_id": data.get("episode_id"),
            "variant_name": data.get("variant_name") or data.get("variant"),
            "usage": data.get("usage") or {},
            "finish_reason": data.get("finish_reason"),
            "output": _extract_output(data),
        }

    def feedback(
        self,
        *,
        metric_name: str,
        value: float | bool,
        inference_id: str | None,
        tags: dict[str, str] | None = None,
    ) -> None:
        if not inference_id:
            return
        payload = {
            "metric_name": metric_name,
            "value": value,
            "inference_id": inference_id,
        }
        if tags:
            payload["tags"] = tags
        response = self._client.post(f"{self.gateway_url}/feedback", json=payload)
        if response.status_code >= 400:
            raise TensorZeroError(
                f"TensorZero feedback failed: {response.status_code} {response.text}"
            )


def _extract_output(data: dict[str, Any]) -> Any:
    output = data.get("output")
    if isinstance(output, dict):
        parsed = output.get("parsed")
        if parsed is not None:
            return parsed
        raw = output.get("raw")
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw
        return output
    if output is not None:
        return output
    for key in ("output", "parsed", "value"):
        if key in data:
            return data[key]
    content = data.get("content")
    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if "text" in item:
                    text_parts.append(str(item["text"]))
                elif "value" in item:
                    return item["value"]
            else:
                text_parts.append(str(item))
        text = "\n".join(text_parts).strip()
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
    if isinstance(content, str):
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return content
    return data
