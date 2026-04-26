"""Local development token issuance DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_LOCAL_DEV_SCOPES = [
    "health:read",
    "parse:read",
    "parse:write",
    "storage:read",
    "storage:write",
    "storage:download",
    "knowledge:read",
    "knowledge:write",
    "eval:read",
    "eval:write",
    "synthesis:read",
    "synthesis:write",
    "jobs:read",
    "jobs:cancel",
]


class LocalDevTokenIssueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str = Field(
        min_length=1,
        max_length=255,
        description=(
            "Required subject identifier for the local development caller. / "
            "本地开发调用方的必填主体标识。"
        ),
        examples=["alice"],
    )
    tenant_id: str = Field(
        min_length=1,
        max_length=255,
        description=(
            "Required tenant boundary that Cortex will apply to the issued token. / "
            "Cortex 将应用到令牌上的必填租户边界。"
        ),
        examples=["tenant_demo"],
    )
    actor_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description=(
            "Optional actor identifier when it differs from `subject`. Best default: omit "
            "and let Cortex fall back to `subject`. / 可选 actor 标识；若与 `subject` "
            "相同，最佳默认值为省略。"
        ),
        examples=["alice"],
    )
    actor_ref: str | None = Field(
        default=None,
        min_length=1,
        max_length=320,
        description=(
            "Optional external reference such as email or employee number. Best default: omit "
            "when no external directory reference exists. / 可选外部引用，如邮箱或工号；"
            "若不存在外部目录引用，最佳默认值为省略。"
        ),
        examples=["alice@example.com"],
    )
    actor_type: str = Field(
        default="user",
        min_length=1,
        max_length=64,
        description=(
            "Optional actor category. Best default: `user`. / "
            "可选 actor 类型，最佳默认值为 `user`。"
        ),
        examples=["user", "service"],
    )
    display_name: str | None = Field(
        default=None,
        max_length=255,
        description=(
            "Optional human-friendly display name copied into the dev token. / "
            "可选展示名，会复制到 dev token 中。"
        ),
        examples=["Alice"],
    )
    client_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description=(
            "Optional client identifier for the local tool or UI issuing requests. / "
            "可选本地工具或 UI 的 client 标识。"
        ),
        examples=["swagger-ui"],
    )
    scopes: list[str] = Field(
        default_factory=lambda: list(DEFAULT_LOCAL_DEV_SCOPES),
        description=(
            "Optional scopes granted to the local dev token. Best default: omit and let Cortex "
            "issue the standard local developer scope bundle. / 可选 scope 集合，最佳默认值为"
            "省略，让 Cortex 自动填入标准本地开发 scope 包。"
        ),
        examples=[["health:read", "parse:write", "jobs:read"]],
    )
    roles: list[str] = Field(
        default_factory=list,
        description=(
            "Optional role keys attached to the caller. Best default: empty list. / "
            "可选角色键集合，最佳默认值为空列表。"
        ),
        examples=[["tenant_admin"]],
    )
    groups: list[str] = Field(
        default_factory=list,
        description=(
            "Optional group memberships used by downstream policy logic. / "
            "可选分组信息，供下游策略判断使用。"
        ),
        examples=[["platform-ops"]],
    )
    expires_in: int = Field(
        default=3600,
        ge=60,
        le=604800,
        description=(
            "Optional token TTL in seconds. Best default: `3600` for local Swagger and smoke "
            "tests. / 可选令牌有效期，单位为秒；本地 Swagger 与冒烟测试的最佳默认值为 `3600`。"
        ),
        examples=[3600],
    )
    additional_claims: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Optional extra claims copied into the dev token payload. / "
            "可选额外 claim，会复制到 dev token 载荷中。"
        ),
        examples=[{"environment": "local"}],
    )


class LocalDevTokenIssueResponse(BaseModel):
    access_token: str
    token_type: Literal["Bearer"] = "Bearer"
    token_format: Literal["dev"] = "dev"
    expires_in: int = Field(ge=1)
    issued_at: datetime
    expires_at: datetime
    scope: str
    subject: str
    tenant_id: str
    issuer: str
    audience: str
    swagger_authorize_value: str = Field(
        description=(
            "Paste this exact value into Swagger UI's `Authorize` dialog. Do not prepend "
            "`Bearer ` manually. / 将这个值原样粘贴到 Swagger UI 的 `Authorize` 弹窗中，"
            "不要手动再加 `Bearer ` 前缀。"
        )
    )
    authorization_header: str = Field(
        description=(
            "Ready-to-use HTTP Authorization header value for curl, Postman, or SDK tests. / "
            "可直接用于 curl、Postman 或 SDK 测试的完整 Authorization 头。"
        )
    )
