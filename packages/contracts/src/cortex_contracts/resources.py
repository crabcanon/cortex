"""Shared resource-oriented DTOs."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .enums import AccessLevel


class AuditFields(BaseModel):
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None
    updated_by: str | None = None


class AccessPolicy(BaseModel):
    access_level: AccessLevel | None = None
    owner_actor_id: str | None = None
    classification_labels: list[str] = Field(default_factory=list)
    allowed_role_keys: list[str] = Field(default_factory=list)
    denied_role_keys: list[str] = Field(default_factory=list)
    purpose_tags: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
