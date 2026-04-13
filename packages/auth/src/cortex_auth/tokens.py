"""Bearer token validation adapters."""

from __future__ import annotations

import base64
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
import jwt
from cortex_common import AuthSettings, json_loads
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


class TokenValidator(Protocol):
    async def validate(self, token: str) -> CallerContext: ...


class DevTokenValidator:
    """Validate locally generated development tokens."""

    async def validate(self, token: str) -> CallerContext:
        if not token.startswith("dev:"):
            raise AuthenticationError("Unsupported dev token format.", code="invalid_dev_token")
        return _caller_from_claims(_decode_dev_payload(token.removeprefix("dev:")))


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
        return TokenValidatorChain((DevTokenValidator(), JwtTokenValidator(settings)))
    if mode == "jwt":
        return JwtTokenValidator(settings)
    if mode == "introspection":
        return IntrospectionTokenValidator(settings)
    if mode == "hybrid":
        return TokenValidatorChain(
            (JwtTokenValidator(settings), IntrospectionTokenValidator(settings))
        )
    raise AuthenticationError(f"Unsupported auth mode `{settings.mode}`.", code="invalid_auth_mode")
