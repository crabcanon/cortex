from __future__ import annotations

import argparse
import json

from rich.console import Console

from .finance_urls import FINANCE_URLS
from .models import ExperimentRequest
from .pipeline import ExperimentPipeline
from .render_tensorzero_config import render_config
from .settings import load_settings

console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the TensorZero + Cortex adaptive A/B example."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_parser = subparsers.add_parser("render-config", help="Render tensorzero.toml from .env.")
    render_parser.add_argument("--env-file", default=None)

    subparsers.add_parser("list-urls", help="Print the built-in finance/economics URL catalog.")

    run_parser = subparsers.add_parser("run", help="Run one Cortex + TensorZero experiment.")
    run_parser.add_argument("--query", default=None)
    run_parser.add_argument("--max-urls", type=int, default=None)
    run_parser.add_argument("--parse-engines", default=None, help="Comma-separated engines.")
    run_parser.add_argument(
        "--parse-mode",
        choices=("sync", "async"),
        default=None,
        help="Use Cortex /v1/parse/sync or /v1/parse/jobs.",
    )
    run_parser.add_argument(
        "--submit-cortex-eval",
        action="store_true",
        default=None,
        help="Override .env and submit the generated dataset to Cortex Evaluation.",
    )
    run_parser.add_argument(
        "--cortex-eval-mode",
        choices=("sync", "async"),
        default=None,
        help=(
            "Use Cortex /v1/eval/sync or /v1/eval/jobs when Cortex Eval submission is enabled."
        ),
    )
    run_parser.add_argument("--skip-knowledge-jobs", action="store_true")

    serve_parser = subparsers.add_parser("serve", help="Run the FastAPI example app.")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8090)

    args = parser.parse_args()
    if args.command == "render-config":
        path = render_config()
        console.print(f"[green]Rendered[/green] {path}")
        return
    if args.command == "list-urls":
        console.print_json(json.dumps(FINANCE_URLS, ensure_ascii=False))
        return
    if args.command == "serve":
        import uvicorn

        uvicorn.run("tensorzero_cortex.main:app", host=args.host, port=args.port, reload=False)
        return

    settings = load_settings()
    parse_engines = (
        [part.strip() for part in args.parse_engines.split(",") if part.strip()]
        if args.parse_engines
        else None
    )
    request = ExperimentRequest(
        query=args.query,
        max_urls=args.max_urls,
        parse_engines=parse_engines,
        parse_mode=args.parse_mode,
        submit_cortex_eval=args.submit_cortex_eval,
        cortex_eval_mode=args.cortex_eval_mode,
        run_knowledge_jobs=not args.skip_knowledge_jobs,
    )
    pipeline = ExperimentPipeline(settings)
    try:
        report = pipeline.run(request)
    finally:
        pipeline.close()
    console.print(f"[green]Run complete[/green] {report.run_id}")
    console.print(f"Report: {report.report_markdown_path}")
    console.print_json(json.dumps(report.scorecard, ensure_ascii=False))
