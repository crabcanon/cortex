"""Parse worker entrypoint."""

import asyncio

from .bootstrap import bootstrap_message, build_worker


def main() -> None:
    """Run one parse worker polling iteration."""
    asyncio.run(_run_once())


async def _run_once() -> None:
    runtime = build_worker()
    try:
        result = await runtime.worker.run_once()
        print(f"{bootstrap_message()}: {result.status}")
    finally:
        await runtime.close()
