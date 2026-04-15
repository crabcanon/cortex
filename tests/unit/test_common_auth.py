"""Focused unit tests for common settings and auth token helpers."""

from __future__ import annotations

import asyncio
import base64
import json

import pytest
from cortex_auth.errors import AuthenticationError
from cortex_auth.issuer import TokenIssuanceUnavailableError, TokenIssueInput, TokenIssuerService
from cortex_auth.models import CallerContext
from cortex_auth.tokens import (
    DevTokenValidator,
    TokenValidatorChain,
    _normalize_values,
    build_token_validator,
)
from cortex_common import AuthSettings, load_settings


def _encode_dev_token(payload: dict[str, object]) -> str:
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    return f"dev:{encoded.rstrip('=')}"


def test_load_settings_parses_bool_flags_and_respects_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORTEX_S3_FORCE_PATH_STYLE", "false")
    monkeypatch.setenv("CORTEX_COGNEE_ENABLED", "true")
    monkeypatch.setenv("CORTEX_OTEL_ENABLED", "0")
    load_settings.cache_clear()

    initial = load_settings()
    monkeypatch.setenv("CORTEX_COGNEE_ENABLED", "false")
    cached = load_settings()
    load_settings.cache_clear()
    refreshed = load_settings()
    load_settings.cache_clear()

    assert initial.s3.force_path_style is False
    assert initial.cognee.enabled is True
    assert initial.telemetry.enabled is False
    assert cached.cognee.enabled is True
    assert refreshed.cognee.enabled is False


def test_normalize_values_accepts_string_sequence_and_scalar() -> None:
    assert _normalize_values("parse:read, parse:write jobs:read") == frozenset(
        {"parse:read", "parse:write", "jobs:read"}
    )
    assert _normalize_values(["admin", "editor"]) == frozenset({"admin", "editor"})
    assert _normalize_values(42) == frozenset({"42"})


@pytest.mark.asyncio
async def test_dev_token_validator_maps_scopes_roles_and_groups() -> None:
    validator = DevTokenValidator()
    caller = await validator.validate(
        _encode_dev_token(
            {
                "sub": "alice",
                "tenant_id": "tenant_auth",
                "scope": "parse:read, parse:write",
                "roles": ["admin", "operator"],
                "groups": "blue green",
                "email": "alice@example.com",
            }
        )
    )

    assert caller.subject == "alice"
    assert caller.actor_id == "alice"
    assert caller.actor_ref == "alice@example.com"
    assert caller.scopes == frozenset({"parse:read", "parse:write"})
    assert caller.roles == frozenset({"admin", "operator"})
    assert caller.groups == frozenset({"blue", "green"})


@pytest.mark.asyncio
async def test_token_validator_chain_falls_back_to_next_validator() -> None:
    class _RejectingValidator:
        async def validate(self, token: str) -> CallerContext:
            del token
            raise AuthenticationError("invalid", code="invalid_token")

    class _AcceptingValidator:
        async def validate(self, token: str) -> CallerContext:
            return CallerContext(
                subject=token,
                actor_id=token,
                tenant_id="tenant_auth",
                scopes=frozenset({"jobs:read"}),
            )

    chain = TokenValidatorChain((_RejectingValidator(), _AcceptingValidator()))
    caller = await chain.validate("alice")

    assert caller.subject == "alice"
    assert caller.scopes == frozenset({"jobs:read"})


def test_build_token_validator_rejects_unknown_mode() -> None:
    with pytest.raises(AuthenticationError, match="Unsupported auth mode"):
        build_token_validator(AuthSettings(CORTEX_AUTH_MODE="custom"))


def test_token_validator_chain_raises_last_error() -> None:
    class _RejectingValidator:
        async def validate(self, token: str) -> CallerContext:
            del token
            raise AuthenticationError("inactive", code="inactive_token")

    chain = TokenValidatorChain((_RejectingValidator(),))

    with pytest.raises(AuthenticationError) as excinfo:
        asyncio.run(chain.validate("alice"))

    assert excinfo.value.code == "inactive_token"


@pytest.mark.asyncio
async def test_token_issuer_service_mints_dev_token_accepted_by_validator() -> None:
    settings = AuthSettings(
        CORTEX_AUTH_MODE="dev",
        CORTEX_AUTH_TOKEN_ISSUER_ENABLED=True,
        CORTEX_AUTH_TOKEN_ISSUER_BOOTSTRAP_SECRET="bootstrap-secret",
    )
    issuer = TokenIssuerService(settings)
    token = issuer.issue_token(
        bootstrap_secret="bootstrap-secret",
        token_input=TokenIssueInput(
            subject="alice",
            tenant_id="tenant_auth",
            scopes=("parse:read", "jobs:read"),
            roles=("admin",),
        ),
    )
    validator = build_token_validator(settings)

    caller = await validator.validate(token.access_token)

    assert token.issued_token_format == "dev"
    assert caller.subject == "alice"
    assert caller.scopes == frozenset({"parse:read", "jobs:read"})
    assert caller.roles == frozenset({"admin"})


@pytest.mark.asyncio
async def test_token_issuer_service_mints_jwt_accepted_by_validator() -> None:
    settings = AuthSettings(
        CORTEX_AUTH_MODE="jwt",
        CORTEX_AUTH_TOKEN_ISSUER_ENABLED=True,
        CORTEX_AUTH_TOKEN_ISSUER_BOOTSTRAP_SECRET="bootstrap-secret",
        CORTEX_AUTH_JWT_SHARED_SECRET="jwt-shared-secret-0123456789abcdef",
    )
    issuer = TokenIssuerService(settings)
    token = issuer.issue_token(
        bootstrap_secret="bootstrap-secret",
        token_input=TokenIssueInput(
            subject="svc-parser",
            tenant_id="tenant_auth",
            scopes=("parse:write",),
            client_id="parser-client",
        ),
    )
    validator = build_token_validator(settings)

    caller = await validator.validate(token.access_token)

    assert token.issued_token_format == "jwt"
    assert caller.subject == "svc-parser"
    assert caller.client_id == "parser-client"
    assert caller.scopes == frozenset({"parse:write"})


def test_token_issuer_service_rejects_introspection_mode() -> None:
    issuer = TokenIssuerService(
        AuthSettings(
            CORTEX_AUTH_MODE="introspection",
            CORTEX_AUTH_TOKEN_ISSUER_ENABLED=True,
            CORTEX_AUTH_TOKEN_ISSUER_BOOTSTRAP_SECRET="bootstrap-secret",
        )
    )

    with pytest.raises(
        TokenIssuanceUnavailableError,
        match="unavailable when auth mode is `introspection`",
    ):
        issuer.issue_token(
            bootstrap_secret="bootstrap-secret",
            token_input=TokenIssueInput(
                subject="alice",
                tenant_id="tenant_auth",
                scopes=("health:read",),
            ),
        )
