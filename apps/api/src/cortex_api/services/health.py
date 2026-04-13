"""Health and readiness service helpers."""

from time import perf_counter

from cortex_common import CortexSettings, utc_now
from cortex_contracts import DependencyCheck, HealthResponse
from cortex_db import SessionFactory
from sqlalchemy import text


async def build_liveness(settings: CortexSettings) -> HealthResponse:
    checks = [
        DependencyCheck(name="api-process", status="ok", detail="Process is accepting requests."),
        DependencyCheck(
            name="telemetry",
            status="ok" if settings.telemetry.enabled else "degraded",
            detail=(
                "OTLP export enabled."
                if settings.telemetry.enabled
                else "Telemetry export disabled."
            ),
        ),
    ]
    status = "ok" if all(check.status == "ok" for check in checks) else "degraded"
    return HealthResponse(
        status=status,
        service="cortex-api",
        mode="live",
        version="0.1.0",
        timestamp=utc_now(),
        checks=checks,
    )


async def build_readiness(
    settings: CortexSettings,
    session_factory: SessionFactory,
) -> tuple[int, HealthResponse]:
    checks: list[DependencyCheck] = []
    overall_status = "ok"

    started = perf_counter()
    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
        checks.append(
            DependencyCheck(
                name="relational-db",
                status="ok",
                latency_ms=int((perf_counter() - started) * 1000),
                detail="Primary metadata database responded successfully.",
            )
        )
    except Exception as exc:
        overall_status = "failed"
        checks.append(
            DependencyCheck(
                name="relational-db",
                status="failed",
                latency_ms=int((perf_counter() - started) * 1000),
                detail=f"Database probe failed: {exc}",
            )
        )

    checks.append(
        DependencyCheck(
            name="auth-config",
            status="ok",
            detail=f"Auth mode `{settings.auth.mode}` is configured.",
        )
    )
    checks.append(
        DependencyCheck(
            name="queue-config",
            status="ok" if settings.queue.url else "degraded",
            detail=(
                "Queue endpoint configured."
                if settings.queue.url
                else "Queue endpoint missing."
            ),
        )
    )
    checks.append(
        DependencyCheck(
            name="telemetry-export",
            status="ok" if settings.telemetry.enabled else "degraded",
            detail=(
                "OTLP exporter configured."
                if settings.telemetry.enabled
                else "Telemetry export disabled."
            ),
        )
    )

    if overall_status != "failed" and any(check.status == "degraded" for check in checks):
        overall_status = "degraded"

    payload = HealthResponse(
        status=overall_status,
        service="cortex-api",
        mode="ready",
        version="0.1.0",
        timestamp=utc_now(),
        checks=checks,
    )
    return (503 if overall_status == "failed" else 200, payload)
