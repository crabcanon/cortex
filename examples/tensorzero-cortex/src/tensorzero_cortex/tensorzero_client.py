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

    def inference(self, *, question: str, context: str, metadata: dict[str, Any]) -> dict[str, Any]:
        user_content = (
            "Question:\n"
            f"{question}\n\n"
            "Cortex Knowledge context:\n"
            f"{context}\n\n"
            "Metadata:\n"
            f"{json.dumps(metadata, ensure_ascii=False)}"
        )
        payload = {
            "function_name": "cortex_rag_answer",
            "input": {"messages": [{"role": "user", "content": user_content}]},
        }
        response = self._client.post(f"{self.gateway_url}/inference", json=payload)
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
            "output": _extract_output(data),
        }

    def feedback(self, *, metric_name: str, value: float | bool, inference_id: str | None) -> None:
        if not inference_id:
            return
        payload = {
            "metric_name": metric_name,
            "value": value,
            "inference_id": inference_id,
        }
        response = self._client.post(f"{self.gateway_url}/feedback", json=payload)
        if response.status_code >= 400:
            raise TensorZeroError(
                f"TensorZero feedback failed: {response.status_code} {response.text}"
            )


def _extract_output(data: dict[str, Any]) -> Any:
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
