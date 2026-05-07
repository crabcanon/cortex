from __future__ import annotations

import argparse
import json

from rich.console import Console

from .finance_urls import FINANCE_URLS
from .knowledge_graph_visualization import (
    KnowledgeGraphVisualizationError,
    latest_run_id,
    visualize_knowledge_graph_from_container,
)
from .models import EvaluationOptions, ExperimentRequest, ParseOptions, TensorZeroOptions
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
    run_parser.add_argument(
        "--tensorzero-strategy",
        choices=("adaptive", "exhaustive", "selected"),
        default=None,
    )
    run_parser.add_argument("--tensorzero-variants", default=None, help="Comma-separated variants.")
    run_parser.add_argument(
        "--context-grouping",
        choices=("combined", "by_parse_engine", "knowledge_or_parse"),
        default=None,
    )
    run_parser.add_argument("--cortex-eval-types", default=None, help="Comma-separated eval types.")
    run_parser.add_argument("--cortex-eval-metric-profile", default=None)

    serve_parser = subparsers.add_parser("serve", help="Run the FastAPI example app.")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8090)

    graph_parser = subparsers.add_parser(
        "visualize-knowledge",
        help="Render Cognee knowledge graph HTML into a TensorZero Cortex artifact folder.",
    )
    graph_parser.add_argument("--run-id", default=None)
    graph_parser.add_argument("--container", default=None)
    graph_parser.add_argument("--output-name", default="knowledge_graph.html")

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
    if args.command == "visualize-knowledge":
        settings = load_settings()
        run_id = args.run_id or latest_run_id()
        try:
            output_path = visualize_knowledge_graph_from_container(
                run_id=run_id,
                container_name=args.container or settings.knowledge_worker_container,
                output_name=args.output_name,
            )
        except KnowledgeGraphVisualizationError as exc:
            console.print(f"[red]Failed[/red] {exc}")
            raise SystemExit(2) from exc
        console.print(f"[green]Rendered[/green] {output_path}")
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
        parse=ParseOptions(
            max_urls=args.max_urls,
            engines=parse_engines,
            mode=args.parse_mode,
        )
        if args.max_urls or parse_engines or args.parse_mode
        else None,
        tensorzero=TensorZeroOptions(
            strategy=args.tensorzero_strategy or settings.tensorzero_strategy,
            variants=_csv_arg(args.tensorzero_variants) or list(settings.tensorzero_variants),
            context_grouping=args.context_grouping or settings.tensorzero_context_grouping,
        )
        if args.tensorzero_strategy or args.tensorzero_variants or args.context_grouping
        else None,
        evaluation=EvaluationOptions(
            enabled=args.submit_cortex_eval
            if args.submit_cortex_eval is not None
            else settings.submit_cortex_eval,
            mode=args.cortex_eval_mode or settings.cortex_eval_mode,
            eval_types=_csv_arg(args.cortex_eval_types) or list(settings.cortex_eval_types),
            metric_profile=args.cortex_eval_metric_profile
            or settings.cortex_eval_metric_profile,
        )
        if (
            args.submit_cortex_eval is not None
            or args.cortex_eval_mode
            or args.cortex_eval_types
            or args.cortex_eval_metric_profile
        )
        else None,
    )
    pipeline = ExperimentPipeline(settings)
    try:
        report = pipeline.run(request)
    finally:
        pipeline.close()
    console.print(f"[green]Run complete[/green] {report.run_id}")
    console.print(f"Report: {report.report_markdown_path}")
    console.print_json(json.dumps(report.scorecard, ensure_ascii=False))


def _csv_arg(value: str | None) -> list[str] | None:
    if not value:
        return None
    values = [part.strip() for part in value.split(",") if part.strip()]
    return values or None
