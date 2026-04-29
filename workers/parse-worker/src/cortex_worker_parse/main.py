"""Parse worker entrypoint."""

import asyncio
import os

from .bootstrap import ParseWorkerRunResult, bootstrap_message, build_worker


def main() -> None:
    """Run the parse worker."""
    if os.getenv("CORTEX_PARSE_WORKER_RUN_ONCE", "").strip().lower() in {"1", "true", "yes"}:
        asyncio.run(_run_once())
        return
    asyncio.run(_run_forever())


async def _run_once() -> None:
    runtime = build_worker()
    try:
        result = await runtime.worker.run_once()
        print(_format_run_result(result))
    finally:
        await runtime.close()


async def _run_forever() -> None:
    sleep_seconds = float(os.getenv("CORTEX_PARSE_WORKER_LOOP_SLEEP_SECONDS", "1"))
    runtime = build_worker()
    print(f"{bootstrap_message()}: succeeded")
    try:
        while True:
            result = await runtime.worker.run_once()
            if result.status != "idle":
                print(_format_run_result(result))
            await asyncio.sleep(sleep_seconds)
    finally:
        await runtime.close()


def _format_run_result(result: ParseWorkerRunResult) -> str:
    parts = [f"cortex parse worker run: {result.status}"]
    if result.job_id:
        parts.append(f"job_id={result.job_id}")
    if result.document_id:
        parts.append(f"document_id={result.document_id}")
    if result.message:
        parts.append(f"message={result.message}")
    return " ".join(parts)
