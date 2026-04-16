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
    access_level: AccessLevel | None = Field(
        default=None,
        description=(
            "Optional coarse-grained data access level. "
            "Best default: omit to let the service apply the resource-type default."
        ),
        examples=["tenant_shared"],
    )
    owner_actor_id: str | None = Field(
        default=None,
        description=(
            "Optional resource owner actor ID. "
            "Best default: omit to let the service infer ownership from the caller."
        ),
        examples=["alice"],
    )
    classification_labels: list[str] = Field(
        default_factory=list,
        description=(
            "Optional classification labels such as `internal` or `restricted`. "
            "Best default: empty list."
        ),
        examples=[["internal", "docs"]],
    )
    allowed_role_keys: list[str] = Field(
        default_factory=list,
        description=(
            "Optional allow-list of roles that may access the resource. "
            "Best default: empty list, meaning no extra allow-list constraint."
        ),
        examples=[["tenant_admin", "analyst"]],
    )
    denied_role_keys: list[str] = Field(
        default_factory=list,
        description=(
            "Optional deny-list of roles that should be blocked even if other checks pass. "
            "Best default: empty list."
        ),
        examples=[["contractor"]],
    )
    purpose_tags: list[str] = Field(
        default_factory=list,
        description=(
            "Optional intended-use tags for ABAC policy evaluation. Best default: empty list."
        ),
        examples=[["knowledge_ingest", "assistant"]],
    )
    constraints: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Optional structured constraints for custom policy engines. Best default: empty object."
        ),
        examples=[{"region": "cn-shanghai"}],
    )
