"""Bearer token validation adapters."""

from __future__ import annotations

import base64
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Protocol

import httpx
import jwt
from cortex_common import (
    AuthSettings,
    ValidationError,
    json_dumps,
    json_loads,
    new_prefixed_id,
    utc_now,
)
from jwt import InvalidTokenError

from .errors import AuthenticationError
from .models import CallerContext


def _normalize_values(value: Any) -> frozenset[str]:
    if value is None:
        return frozenset()
    if isinstance(value, str):
        return frozenset(part for part in value.replace(",", " ").split() if part)
    if isinstance(value, Sequence):
        return frozenset(str(part) for part in value if part)
    return frozenset({str(value)})


def _decode_dev_payload(encoded: str) -> dict[str, Any]:
    padding = "=" * (-len(encoded) % 4)
    try:
        raw = base64.urlsafe_b64decode(f"{encoded}{padding}".encode("ascii")).decode("utf-8")
    except Exception as exc:  # pragma: no cover - defensive
        raise AuthenticationError("Invalid dev token payload.", code="invalid_dev_token") from exc
    payload = json_loads(raw)
    if not isinstance(payload, dict):
        raise AuthenticationError(
            "Dev token payload must be a JSON object.",
            code="invalid_dev_token",
        )
    return payload


def _encode_dev_payload(payload: dict[str, Any]) -> str:
    encoded = base64.urlsafe_b64encode(json_dumps(payload).encode("utf-8")).decode("ascii")
    return f"dev:{encoded.rstrip('=')}"


def _caller_from_claims(claims: dict[str, Any]) -> CallerContext:
    subject = str(claims.get("sub") or "").strip()
    tenant_id = str(claims.get("tenant_id") or "").strip()
    if not subject:
        raise AuthenticationError("Token is missing `sub`.", code="token_subject_missing")
    if not tenant_id:
        raise AuthenticationError("Token is missing `tenant_id`.", code="token_tenant_missing")
    actor_id = str(claims.get("actor_id") or subject).strip() or subject
    actor_ref = claims.get("actor_ref") or claims.get("email") or subject
    return CallerContext(
        subject=subject,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_ref=str(actor_ref) if actor_ref else None,
        actor_type=str(claims.get("actor_type") or "user"),
        display_name=str(claims.get("name")) if claims.get("name") else None,
        client_id=str(claims.get("client_id")) if claims.get("client_id") else None,
        scopes=_normalize_values(claims.get("scope") or claims.get("scopes")),
        roles=_normalize_values(claims.get("roles")),
        groups=_normalize_values(claims.get("groups")),
        token_id=str(claims.get("jti")) if claims.get("jti") else None,
        raw_claims=claims,
    )


DEFAULT_LOCAL_DEV_SCOPES: tuple[str, ...] = (
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
)
DEFAULT_LOCAL_DEV_EXPIRES_IN = 3600
_RESERVED_LOCAL_DEV_CLAIMS = frozenset(
    {
        "sub",
        "tenant_id",
        "actor_id",
        "actor_ref",
        "actor_type",
        "name",
        "client_id",
        "scope",
        "scopes",
        "roles",
        "groups",
        "iat",
        "nbf",
        "exp",
        "iss",
        "aud",
        "jti",
    }
)


@dataclass(slots=True)
class LocalDevTokenIssueInput:
    subject: str
    tenant_id: str
    actor_id: str | None = None
    actor_ref: str | None = None
    actor_type: str = "user"
    display_name: str | None = None
    client_id: str | None = None
    scopes: tuple[str, ...] = ()
    roles: tuple[str, ...] = ()
    groups: tuple[str, ...] = ()
    expires_in: int = DEFAULT_LOCAL_DEV_EXPIRES_IN
    additional_claims: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LocalDevTokenIssueResult:
    access_token: str
    expires_in: int
    issued_at: datetime
    expires_at: datetime
    scope: str
    subject: str
    tenant_id: str
    issuer: str
    audience: str
    authorization_header: str


def _validate_temporal_claims(claims: dict[str, Any], *, clock_skew_seconds: int) -> None:
    now = int(utc_now().timestamp())
    exp = claims.get("exp")
    if exp is not None and int(exp) + clock_skew_seconds < now:
        raise AuthenticationError("Dev token has expired.", code="dev_token_expired")
    nbf = claims.get("nbf")
    if nbf is not None and int(nbf) - clock_skew_seconds > now:
        raise AuthenticationError("Dev token is not active yet.", code="dev_token_not_yet_valid")
    iat = claims.get("iat")
    if iat is not None and int(iat) - clock_skew_seconds > now:
        raise AuthenticationError(
            "Dev token issue time is in the future.",
            code="dev_token_invalid",
        )


def _validate_dev_issuer_and_audience(claims: dict[str, Any], settings: AuthSettings) -> None:
    issuer = claims.get("iss")
    if issuer is not None and settings.oidc_issuer and str(issuer) != settings.oidc_issuer:
        raise AuthenticationError(
            "Dev token issuer does not match runtime settings.",
            code="invalid_dev_token",
        )
    audience = claims.get("aud")
    if audience is None or not settings.oidc_audience:
        return
    audiences = _normalize_values(audience)
    if settings.oidc_audience not in audiences:
        raise AuthenticationError(
            "Dev token audience does not match runtime settings.",
            code="invalid_dev_token",
        )


def issue_local_dev_token(
    settings: AuthSettings,
    token_input: LocalDevTokenIssueInput,
) -> LocalDevTokenIssueResult:
    overlapping_claims = _RESERVED_LOCAL_DEV_CLAIMS.intersection(token_input.additional_claims)
    if overlapping_claims:
        conflict_list = ", ".join(sorted(overlapping_claims))
        raise ValidationError(
            "Additional claims reuse reserved token fields.",
            extra={
                "field_errors": [
                    {
                        "field": "body.additional_claims",
                        "message": f"Reserved claims cannot be overridden: {conflict_list}",
                    }
                ]
            },
        )

    subject = token_input.subject.strip()
    tenant_id = token_input.tenant_id.strip()
    if not subject or not tenant_id:
        raise ValidationError(
            "Subject and tenant_id are required for local dev tokens.",
            extra={
                "field_errors": [
                    {"field": "body.subject", "message": "Field required."},
                    {"field": "body.tenant_id", "message": "Field required."},
                ]
            },
        )

    scopes = tuple(dict.fromkeys(token_input.scopes or DEFAULT_LOCAL_DEV_SCOPES))
    roles = tuple(dict.fromkeys(token_input.roles))
    groups = tuple(dict.fromkeys(token_input.groups))
    issued_at = utc_now()
    expires_in = token_input.expires_in or DEFAULT_LOCAL_DEV_EXPIRES_IN
    expires_at = issued_at + timedelta(seconds=expires_in)
    claims: dict[str, Any] = {
        "sub": subject,
        "tenant_id": tenant_id,
        "actor_id": (token_input.actor_id or subject).strip() or subject,
        "actor_type": token_input.actor_type,
        "scope": " ".join(scopes),
        "roles": list(roles),
        "groups": list(groups),
        "iat": int(issued_at.timestamp()),
        "nbf": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": settings.oidc_issuer,
        "aud": settings.oidc_audience,
        "jti": new_prefixed_id("devtok"),
    }
    if token_input.actor_ref:
        claims["actor_ref"] = token_input.actor_ref
    if token_input.display_name:
        claims["name"] = token_input.display_name
    if token_input.client_id:
        claims["client_id"] = token_input.client_id
    claims.update(token_input.additional_claims)
    access_token = _encode_dev_payload(claims)
    return LocalDevTokenIssueResult(
        access_token=access_token,
        expires_in=expires_in,
        issued_at=issued_at,
        expires_at=expires_at,
        scope=" ".join(scopes),
        subject=subject,
        tenant_id=tenant_id,
        issuer=settings.oidc_issuer,
        audience=settings.oidc_audience,
        authorization_header=f"Bearer {access_token}",
    )


class TokenValidator(Protocol):
    async def validate(self, token: str) -> CallerContext: ...


class DevTokenValidator:
    """Validate locally generated development tokens."""

    def __init__(self, settings: AuthSettings) -> None:
        self._settings = settings

    async def validate(self, token: str) -> CallerContext:
        if not token.startswith("dev:"):
            raise AuthenticationError("Unsupported dev token format.", code="invalid_dev_token")
        claims = _decode_dev_payload(token.removeprefix("dev:"))
        _validate_temporal_claims(claims, clock_skew_seconds=self._settings.clock_skew_seconds)
        _validate_dev_issuer_and_audience(claims, self._settings)
        return _caller_from_claims(claims)


class JwtTokenValidator:
    """Validate self-contained JWT bearer tokens."""

    def __init__(self, settings: AuthSettings) -> None:
        self._settings = settings

    async def validate(self, token: str) -> CallerContext:
        audience = self._settings.oidc_audience or None
        issuer = self._settings.oidc_issuer or None
        try:
            claims = jwt.decode(
                token,
                self._settings.jwt_shared_secret,
                algorithms=[self._settings.jwt_algorithm],
                audience=audience,
                issuer=issuer,
                options={
                    "verify_aud": audience is not None,
                    "verify_iss": issuer is not None,
                },
                leeway=self._settings.clock_skew_seconds,
            )
        except InvalidTokenError as exc:
            raise AuthenticationError("JWT validation failed.", code="invalid_jwt") from exc
        if not isinstance(claims, dict):  # pragma: no cover - defensive
            raise AuthenticationError("JWT claims must be an object.", code="invalid_jwt")
        return _caller_from_claims(claims)


class IntrospectionTokenValidator:
    """Validate opaque tokens using an OAuth2 introspection endpoint."""

    def __init__(self, settings: AuthSettings) -> None:
        self._settings = settings

    async def validate(self, token: str) -> CallerContext:
        if not self._settings.introspection_url:
            raise AuthenticationError(
                "Token introspection is not configured.",
                code="introspection_not_configured",
            )
        auth: tuple[str, str] | None = None
        if self._settings.introspection_client_id and self._settings.introspection_client_secret:
            auth = (
                self._settings.introspection_client_id,
                self._settings.introspection_client_secret,
            )
        async with httpx.AsyncClient(timeout=5.0) as client:
            request_kwargs: dict[str, Any] = {"data": {"token": token}}
            if auth is not None:
                request_kwargs["auth"] = auth
            response = await client.post(self._settings.introspection_url, **request_kwargs)
        if response.status_code >= 400:
            raise AuthenticationError(
                "Token introspection failed.",
                code="introspection_failed",
            )
        payload = response.json()
        if not isinstance(payload, dict) or not payload.get("active"):
            raise AuthenticationError("Token is inactive.", code="inactive_token")
        return _caller_from_claims(payload)


@dataclass(slots=True)
class TokenValidatorChain:
    validators: tuple[TokenValidator, ...]

    async def validate(self, token: str) -> CallerContext:
        last_error: AuthenticationError | None = None
        for validator in self.validators:
            try:
                return await validator.validate(token)
            except AuthenticationError as exc:
                last_error = exc
        raise last_error or AuthenticationError("No token validator is configured.")


def build_token_validator(settings: AuthSettings) -> TokenValidator:
    mode = settings.mode.lower()
    if mode == "dev":
        return TokenValidatorChain((DevTokenValidator(settings), JwtTokenValidator(settings)))
    if mode == "jwt":
        return JwtTokenValidator(settings)
    if mode == "introspection":
        return IntrospectionTokenValidator(settings)
    if mode == "hybrid":
        return TokenValidatorChain(
            (JwtTokenValidator(settings), IntrospectionTokenValidator(settings))
        )
    raise AuthenticationError(f"Unsupported auth mode `{settings.mode}`.", code="invalid_auth_mode")
