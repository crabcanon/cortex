"""Authentication and token issuance DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

BOOTSTRAP_GRANT_TYPE = "urn:cortex:params:oauth:grant-type:bootstrap"


class TokenIssueRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "grant_type": BOOTSTRAP_GRANT_TYPE,
                    "subject": "alice",
                    "tenant_id": "tenant_demo",
                    "actor_id": "alice",
                    "actor_ref": "alice@example.com",
                    "actor_type": "user",
                    "display_name": "Alice",
                    "client_id": "swagger-ui",
                    "scopes": [
                        "health:read",
                        "parse:read",
                        "parse:write",
                        "storage:read",
                        "storage:write",
                        "knowledge:read",
                        "knowledge:write",
                        "jobs:read",
                    ],
                    "roles": ["tenant_admin"],
                    "groups": ["platform-ops"],
                    "expires_in": 3600,
                    "additional_claims": {"environment": "local"},
                }
            ]
        },
    )

    grant_type: Literal["urn:cortex:params:oauth:grant-type:bootstrap"] = Field(
        default=BOOTSTRAP_GRANT_TYPE,
        description=(
            "Grant type used by Cortex's built-in bootstrap token issuer. "
            "Keep the default value unless the API contract changes."
        ),
        examples=[BOOTSTRAP_GRANT_TYPE],
    )
    subject: str = Field(
        min_length=1,
        max_length=255,
        description=(
            "Required subject identifier for the issued token. "
            "Use a stable user, service, or workload identity."
        ),
        examples=["alice"],
    )
    tenant_id: str = Field(
        min_length=1,
        max_length=255,
        description=(
            "Required tenant boundary applied to the token. "
            "Authorization decisions are scoped to this tenant."
        ),
        examples=["tenant_demo"],
    )
    actor_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description=(
            "Optional actor identifier when it differs from `subject`. "
            "Best default: omit to let downstream systems fall back to `subject`."
        ),
        examples=["alice"],
    )
    actor_ref: str | None = Field(
        default=None,
        min_length=1,
        max_length=320,
        description=(
            "Optional external reference such as email, employee ID, or service account name. "
            "Best default: omit when no external directory reference exists."
        ),
        examples=["alice@example.com"],
    )
    actor_type: str = Field(
        default="user",
        min_length=1,
        max_length=64,
        description=(
            "Optional actor category. Best default: `user` for human callers; "
            "use `service` for automation."
        ),
        examples=["user", "service"],
    )
    display_name: str | None = Field(
        default=None,
        max_length=255,
        description=(
            "Optional human-friendly display name embedded in the token. "
            "Best default: omit to avoid duplicating directory data."
        ),
        examples=["Alice"],
    )
    client_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description=(
            "Optional client identifier for the calling app or integration. "
            "Best default: omit unless a downstream audit flow expects it."
        ),
        examples=["swagger-ui"],
    )
    scopes: list[str] = Field(
        min_length=1,
        description=(
            "Required OAuth scopes granted to the token. Include only the API capabilities "
            "the caller truly needs."
        ),
        examples=[["health:read", "parse:write", "jobs:read"]],
    )
    roles: list[str] = Field(
        default_factory=list,
        description=(
            "Optional RBAC role keys attached to the caller. "
            "Best default: empty list when scope-based access is sufficient."
        ),
        examples=[["tenant_admin"]],
    )
    groups: list[str] = Field(
        default_factory=list,
        description=(
            "Optional group memberships used by downstream policy logic. Best default: empty list."
        ),
        examples=[["platform-ops"]],
    )
    expires_in: int | None = Field(
        default=None,
        ge=60,
        le=86400,
        description=(
            "Optional token TTL in seconds. Best default: omit and use the deployment's "
            "configured default TTL."
        ),
        examples=[3600],
    )
    additional_claims: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Optional extra claims copied into the token payload. Best default: empty object."
        ),
        examples=[{"environment": "local"}],
    )


class TokenIssueResponse(BaseModel):
    access_token: str
    token_type: Literal["Bearer"] = "Bearer"
    issued_token_format: Literal["dev", "jwt"]
    expires_in: int = Field(ge=1)
    issued_at: datetime
    expires_at: datetime
    scope: str
    subject: str
    tenant_id: str
    issuer: str
    audience: str
