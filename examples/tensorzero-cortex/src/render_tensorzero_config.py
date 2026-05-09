from __future__ import annotations

import os
from pathlib import Path
from string import Template

from dotenv import load_dotenv
from settings import ROOT, TENSORZERO_DIR


def render_config(env_file: Path | None = None) -> Path:
    env_file = _resolve_env_file(env_file)
    if not env_file.exists():
        raise FileNotFoundError(
            f"TensorZero Cortex env file was not found: {env_file}. "
            "Copy .env.example to .env and fill every model/provider value used by "
            "tensorzero/tensorzero.toml.tpl."
        )
    load_dotenv(env_file, override=True)
    template_path = TENSORZERO_DIR / "tensorzero.toml.tpl"
    output_path = TENSORZERO_DIR / "tensorzero.toml"
    template_text = template_path.read_text(encoding="utf-8")
    values = _template_values(template_text)
    rendered = Template(template_text).substitute(values)
    output_path.write_text(rendered, encoding="utf-8")
    return output_path


def _resolve_env_file(env_file: Path | None) -> Path:
    if env_file is None:
        return ROOT / ".env"
    if env_file.is_absolute() or env_file.exists():
        return env_file
    return ROOT / env_file


def _template_values(template_text: str) -> dict[str, str]:
    keys = sorted(set(_template_keys(template_text)))
    missing = [key for key in keys if not _env_value(key)]
    if missing:
        raise ValueError(
            "Missing TensorZero config environment values: "
            + ", ".join(missing)
            + ". Put them in examples/tensorzero-cortex/.env; "
            "render_tensorzero_config.py intentionally has no fallback defaults."
        )
    return {key: _normalize_value(key, _env_value(key) or "") for key in keys}


def _template_keys(template_text: str) -> list[str]:
    keys: list[str] = []
    for match in Template.pattern.finditer(template_text):
        name = match.group("named") or match.group("braced")
        if name:
            keys.append(name)
    return keys


def _env_value(key: str) -> str | None:
    value = os.getenv(key)
    if value is None or not value.strip():
        return None
    return value.strip()


def _normalize_value(key: str, value: str) -> str:
    if key.endswith("_BASE_URL"):
        return value.rstrip("/")
    return value


if __name__ == "__main__":
    path = render_config()
    print(f"Rendered {path}")
