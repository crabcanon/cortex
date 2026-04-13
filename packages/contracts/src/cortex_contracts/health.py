"""Health and readiness DTOs."""

from datetime import datetime

from pydantic import BaseModel, Field


class DependencyCheck(BaseModel):
    name: str
    status: str
    latency_ms: int | None = Field(default=None, ge=0)
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str
    service: str
    mode: str
    version: str
    timestamp: datetime
    checks: list[DependencyCheck] = Field(default_factory=list)
