"""Authentication and token issuance DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

BOOTSTRAP_GRANT_TYPE = "urn:cortex:params:oauth:grant-type:bootstrap"


class TokenIssueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grant_type: Literal["urn:cortex:params:oauth:grant-type:bootstrap"] = BOOTSTRAP_GRANT_TYPE
    subject: str = Field(min_length=1, max_length=255)
    tenant_id: str = Field(min_length=1, max_length=255)
    actor_id: str | None = Field(default=None, min_length=1, max_length=255)
    actor_ref: str | None = Field(default=None, min_length=1, max_length=320)
    actor_type: str = Field(default="user", min_length=1, max_length=64)
    display_name: str | None = Field(default=None, max_length=255)
    client_id: str | None = Field(default=None, min_length=1, max_length=255)
    scopes: list[str] = Field(min_length=1)
    roles: list[str] = Field(default_factory=list)
    groups: list[str] = Field(default_factory=list)
    expires_in: int | None = Field(default=None, ge=60, le=86400)
    additional_claims: dict[str, Any] = Field(default_factory=dict)


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
