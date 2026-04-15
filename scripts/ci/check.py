"""Cross-platform CI entrypoint for Cortex repository validation."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_step(label: str, command: list[str]) -> None:
    print(f"[cortex] {label}...")
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Cortex validation steps in a cross-platform way."
    )
    parser.add_argument(
        "--skip-yaml",
        action="store_true",
        help="Skip YAML/OpenAPI validation.",
    )
    parser.add_argument(
        "--skip-lint",
        action="store_true",
        help="Skip Ruff linting.",
    )
    parser.add_argument(
        "--skip-types",
        action="store_true",
        help="Skip Pyright type-checking.",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip pytest execution.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        if not args.skip_yaml:
            _run_step(
                "validating YAML/OpenAPI assets",
                [sys.executable, str(REPO_ROOT / "scripts" / "ci" / "validate_yaml.py")],
            )
        if not args.skip_lint:
            _run_step("running Ruff", ["ruff", "check", "."])
        if not args.skip_types:
            _run_step("running Pyright", ["pyright"])
        if not args.skip_tests:
            _run_step("running pytest", ["pytest"])
    except subprocess.CalledProcessError as exc:
        print(
            f"[cortex] step failed with exit code {exc.returncode}: {' '.join(exc.cmd)}",
            file=sys.stderr,
        )
        return exc.returncode

    print("[cortex] checks complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
