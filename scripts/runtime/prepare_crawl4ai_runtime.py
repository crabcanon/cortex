"""Prepare the Crawl4AI + Playwright runtime for local or deployed processes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cortex_common import load_runtime_config, load_settings
from cortex_parse import (
    classify_crawl4ai_playwright_failure,
    prepare_crawl4ai_playwright_runtime,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare the Crawl4AI Playwright runtime and optionally install browsers."
    )
    parser.add_argument(
        "--runtime-config",
        default=None,
        help="Optional override path for the unified runtime config file.",
    )
    parser.add_argument(
        "--install-if-missing",
        action="store_true",
        help="Install the configured Playwright browser if probe fails.",
    )
    parser.add_argument(
        "--with-deps",
        action="store_true",
        help="Pass --with-deps to `python -m playwright install` when auto-installing.",
    )
    parser.add_argument(
        "--no-probe",
        action="store_true",
        help="Skip active browser launch probing after preparing the environment.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a JSON summary instead of human-readable text.",
    )
    args = parser.parse_args()

    settings = load_settings()
    runtime_path = args.runtime_config or settings.runtime.path
    runtime_config = load_runtime_config(runtime_path)
    try:
        runtime = prepare_crawl4ai_playwright_runtime(
            runtime_config,
            install_if_missing=args.install_if_missing,
            with_deps=args.with_deps,
            probe=not args.no_probe,
        )
    except Exception as exc:
        failure = classify_crawl4ai_playwright_failure(exc)
        payload = {
            "status": "error",
            "error_code": failure.code,
            "detail": str(exc),
            "runtime_config_path": str(Path(runtime_path)),
            "hints": list(failure.hints),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False))
        else:
            print("[cortex] Crawl4AI runtime preparation failed.", file=sys.stderr)
            print(f"[cortex] category: {failure.code}", file=sys.stderr)
            print(f"[cortex] detail: {exc}", file=sys.stderr)
            for hint in failure.hints:
                print(f"[cortex] hint: {hint}", file=sys.stderr)
        raise SystemExit(2) from exc

    payload = {
        "status": "ok",
        "enabled": runtime.enabled,
        "runtime_config_path": str(Path(runtime_path)),
        "base_directory": str(runtime.base_directory),
        "playwright_browsers_path": str(runtime.browsers_path),
        "browser_name": runtime.browser_name,
        "validate_on_startup": runtime.validate_on_startup,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
        return

    print(
        "[cortex] Crawl4AI runtime prepared: "
        f"enabled={runtime.enabled}, browser={runtime.browser_name}, "
        f"base_dir={runtime.base_directory}, browsers_path={runtime.browsers_path}"
    )


if __name__ == "__main__":
    main()
