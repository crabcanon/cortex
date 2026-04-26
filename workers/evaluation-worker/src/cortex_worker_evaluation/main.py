"""CLI entrypoint for the evaluation worker."""

from __future__ import annotations

import asyncio

from .bootstrap import build_worker


async def _run() -> None:
    runtime = build_worker()
    try:
        result = await runtime.worker.run_once()
        if result.message:
            print(result.message)
    finally:
        await runtime.close()


def main() -> None:
    asyncio.run(_run())
