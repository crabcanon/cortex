from __future__ import annotations

import os
from pathlib import Path
from string import Template

from dotenv import load_dotenv

from .settings import ROOT, TENSORZERO_DIR

DEFAULTS = {
    "OPENAI_BASE_URL": "https://api.openai.com/v1",
    "OPENAI_MODEL_ID": "gpt-4.1-mini",
    "GEMINI_BASE_URL": "https://generativelanguage.googleapis.com/v1beta/openai",
    "GEMINI_MODEL_ID": "gemini-2.5-flash",
    "KIMI_BASE_URL": "https://api.moonshot.cn/v1",
    "KIMI_MODEL_ID": "kimi-k2-0905-preview",
}


def render_config(env_file: Path | None = None) -> Path:
    if env_file is None:
        env_file = ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    template_path = TENSORZERO_DIR / "tensorzero.toml.tpl"
    output_path = TENSORZERO_DIR / "tensorzero.toml"
    values = {key: os.getenv(key, default).rstrip("/") for key, default in DEFAULTS.items()}
    rendered = Template(template_path.read_text(encoding="utf-8")).safe_substitute(values)
    output_path.write_text(rendered, encoding="utf-8")
    return output_path


if __name__ == "__main__":
    path = render_config()
    print(f"Rendered {path}")
