from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts"
TENSORZERO_DIR = ROOT / "tensorzero"


@dataclass(frozen=True)
class Settings:
    cortex_base_url: str
    cortex_bearer_token: str | None
    cortex_tenant_id: str
    cortex_actor_id: str
    tensorzero_gateway_url: str
    tensorzero_ui_url: str
    tensorzero_ready_timeout_seconds: float
    parse_engines: tuple[str, ...]
    parse_mode: str
    default_query: str
    max_urls: int
    knowledge_search_type: str
    submit_cortex_eval: bool
    cortex_eval_mode: str
    request_timeout_seconds: float


def load_settings(env_file: Path | None = None) -> Settings:
    if env_file is None:
        env_file = ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=True)

    parse_engines = tuple(
        part.strip()
        for part in os.getenv("PARSE_ENGINES", "auto,crawl4ai,jina_reader,markitdown").split(",")
        if part.strip()
    )
    return Settings(
        cortex_base_url=_env("CORTEX_BASE_URL", "http://127.0.0.1:8080").rstrip("/"),
        cortex_bearer_token=_optional_env("CORTEX_BEARER_TOKEN"),
        cortex_tenant_id=_env("CORTEX_TENANT_ID", "tenant_demo"),
        cortex_actor_id=_env("CORTEX_ACTOR_ID", "tensorzero-cortex-demo"),
        tensorzero_gateway_url=_env("TENSORZERO_GATEWAY_URL", "http://127.0.0.1:3002").rstrip("/"),
        tensorzero_ui_url=_env("TENSORZERO_UI_URL", "http://127.0.0.1:4000").rstrip("/"),
        tensorzero_ready_timeout_seconds=float(_env("TENSORZERO_READY_TIMEOUT_SECONDS", "180")),
        parse_engines=parse_engines or ("auto",),
        parse_mode=_env("PARSE_MODE", "sync").lower(),
        default_query=_env(
            "DEFAULT_QUERY",
            "What are the key macroeconomic and financial stability risks "
            "mentioned in the documents?",
        ),
        max_urls=int(_env("MAX_URLS", "5")),
        knowledge_search_type=_env("KNOWLEDGE_SEARCH_TYPE", "CHUNKS"),
        submit_cortex_eval=_env("SUBMIT_CORTEX_EVAL", "false").lower() == "true",
        cortex_eval_mode=_env("CORTEX_EVAL_MODE", "sync").lower(),
        request_timeout_seconds=float(_env("REQUEST_TIMEOUT_SECONDS", "120")),
    )


def _env(key: str, default: str) -> str:
    value = os.getenv(key)
    if value is None or not value.strip():
        return default
    return value.strip()


def _optional_env(key: str) -> str | None:
    value = os.getenv(key)
    if value is None or not value.strip():
        return None
    return value.strip()
