"""Focused unit tests for common settings and auth token helpers."""

from __future__ import annotations

import asyncio
import base64
import json

import pytest
from cortex_auth.errors import AuthenticationError
from cortex_auth.models import CallerContext
from cortex_auth.tokens import (
    DEFAULT_LOCAL_DEV_SCOPES,
    DevTokenValidator,
    LocalDevTokenIssueInput,
    TokenValidatorChain,
    _normalize_values,
    build_token_validator,
    issue_local_dev_token,
)
from cortex_common import AuthSettings, ValidationError, load_settings


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
    validator = DevTokenValidator(AuthSettings())
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


def test_issue_local_dev_token_uses_standard_scope_bundle_by_default() -> None:
    result = issue_local_dev_token(
        AuthSettings(),
        LocalDevTokenIssueInput(
            subject="alice",
            tenant_id="tenant_demo",
        ),
    )

    assert result.access_token.startswith("dev:")
    assert result.scope == " ".join(DEFAULT_LOCAL_DEV_SCOPES)
    assert result.authorization_header == f"Bearer {result.access_token}"


@pytest.mark.asyncio
async def test_dev_token_validator_rejects_expired_token() -> None:
    settings = AuthSettings()
    token = _encode_dev_token(
        {
            "sub": "alice",
            "tenant_id": "tenant_demo",
            "actor_id": "alice",
            "exp": 1,
            "iss": settings.oidc_issuer,
            "aud": settings.oidc_audience,
        }
    )
    validator = DevTokenValidator(settings)

    with pytest.raises(AuthenticationError, match="expired"):
        await validator.validate(token)


def test_issue_local_dev_token_rejects_reserved_claim_overrides() -> None:
    with pytest.raises(ValidationError, match="reserved token fields"):
        issue_local_dev_token(
            AuthSettings(),
            LocalDevTokenIssueInput(
                subject="alice",
                tenant_id="tenant_demo",
                additional_claims={"sub": "mallory"},
            ),
        )
