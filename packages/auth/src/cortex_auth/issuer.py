"""Optional built-in token issuance helpers for local/self-hosted deployments."""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from secrets import compare_digest
from typing import Any

import jwt
from cortex_common import (
    AuthSettings,
    ConfigError,
    CortexError,
    ValidationError,
    new_prefixed_id,
    utc_now,
)

from .errors import AuthenticationError


@dataclass(slots=True)
class TokenIssueInput:
    subject: str
    tenant_id: str
    scopes: tuple[str, ...]
    actor_id: str | None = None
    actor_ref: str | None = None
    actor_type: str = "user"
    display_name: str | None = None
    client_id: str | None = None
    roles: tuple[str, ...] = ()
    groups: tuple[str, ...] = ()
    expires_in: int | None = None
    additional_claims: Mapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TokenIssueResult:
    access_token: str
    issued_token_format: str
    expires_in: int
    issued_at: datetime
    expires_at: datetime
    scope: str
    subject: str
    tenant_id: str
    issuer: str
    audience: str


class TokenIssuanceUnavailableError(CortexError):
    """Raised when the optional built-in token issuer is not available."""

    def __init__(self, code: str, detail: str, status_code: int = 503) -> None:
        super().__init__(code, detail, status_code, {})


class TokenIssuerService:
    """Mint dev or shared-secret JWT access tokens behind a bootstrap secret."""

    _RESERVED_CLAIMS = frozenset(
        {
            "iss",
            "aud",
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
            "jti",
        }
    )
    _HMAC_ALGORITHMS = frozenset({"HS256", "HS384", "HS512"})

    def __init__(self, settings: AuthSettings) -> None:
        self._settings = settings

    def authenticate_bootstrap_secret(self, presented_secret: str | None) -> None:
        self._resolve_token_format()
        if not presented_secret:
            raise AuthenticationError(
                "Bootstrap issuer secret is required.",
                code="missing_issuer_secret",
            )
        expected_secret = self._settings.token_issuer_bootstrap_secret or ""
        if not compare_digest(presented_secret, expected_secret):
            raise AuthenticationError(
                "Bootstrap issuer secret is invalid.",
                code="invalid_issuer_secret",
            )

    def issue_token(
        self,
        *,
        bootstrap_secret: str | None,
        token_input: TokenIssueInput,
    ) -> TokenIssueResult:
        token_format = self._resolve_token_format()
        self.authenticate_bootstrap_secret(bootstrap_secret)
        if not token_input.scopes:
            raise ValidationError("At least one scope is required.")

        additional_claims = dict(token_input.additional_claims)
        reserved_overrides = sorted(self._RESERVED_CLAIMS.intersection(additional_claims))
        if reserved_overrides:
            raise ValidationError(
                "additional_claims cannot override reserved claims: "
                + ", ".join(reserved_overrides)
            )

        issued_at = utc_now()
        requested_ttl = token_input.expires_in or self._settings.token_default_ttl_seconds
        expires_in = min(requested_ttl, self._settings.token_max_ttl_seconds)
        if expires_in < 60:
            raise ValidationError("expires_in must be at least 60 seconds.")
        expires_at = issued_at + timedelta(seconds=expires_in)

        scopes = tuple(sorted({scope.strip() for scope in token_input.scopes if scope.strip()}))
        if not scopes:
            raise ValidationError("At least one scope is required.")

        claims: dict[str, Any] = {
            "iss": self._settings.oidc_issuer,
            "aud": self._settings.oidc_audience,
            "sub": token_input.subject,
            "tenant_id": token_input.tenant_id,
            "actor_id": token_input.actor_id or token_input.subject,
            "actor_ref": token_input.actor_ref or token_input.subject,
            "actor_type": token_input.actor_type,
            "scope": " ".join(scopes),
            "roles": sorted({role.strip() for role in token_input.roles if role.strip()}),
            "groups": sorted({group.strip() for group in token_input.groups if group.strip()}),
            "iat": int(issued_at.timestamp()),
            "nbf": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
            "jti": new_prefixed_id("token"),
        }
        if token_input.display_name:
            claims["name"] = token_input.display_name
        if token_input.client_id:
            claims["client_id"] = token_input.client_id
        claims.update(additional_claims)

        if token_format == "dev":
            raw_payload = json.dumps(claims, separators=(",", ":")).encode("utf-8")
            encoded = base64.urlsafe_b64encode(raw_payload).decode("ascii").rstrip("=")
            access_token = f"dev:{encoded}"
        else:
            access_token = jwt.encode(
                claims,
                self._settings.jwt_shared_secret,
                algorithm=self._settings.jwt_algorithm,
            )

        return TokenIssueResult(
            access_token=access_token,
            issued_token_format=token_format,
            expires_in=expires_in,
            issued_at=issued_at,
            expires_at=expires_at,
            scope=" ".join(scopes),
            subject=token_input.subject,
            tenant_id=token_input.tenant_id,
            issuer=self._settings.oidc_issuer,
            audience=self._settings.oidc_audience,
        )

    def _resolve_token_format(self) -> str:
        if not self._settings.token_issuer_enabled:
            raise TokenIssuanceUnavailableError(
                "token_issuer_disabled",
                "The built-in token issuer is disabled for this deployment.",
            )
        if not self._settings.token_issuer_bootstrap_secret:
            raise ConfigError(
                "CORTEX_AUTH_TOKEN_ISSUER_ENABLED=true requires "
                "CORTEX_AUTH_TOKEN_ISSUER_BOOTSTRAP_SECRET to be configured."
            )

        mode = self._settings.mode.lower()
        if mode == "dev":
            return "dev"
        if mode in {"jwt", "hybrid"}:
            algorithm = self._settings.jwt_algorithm.upper()
            if algorithm not in self._HMAC_ALGORITHMS:
                raise ConfigError(
                    "The built-in token issuer currently supports only HMAC JWT "
                    f"algorithms ({', '.join(sorted(self._HMAC_ALGORITHMS))})."
                )
            return "jwt"
        raise TokenIssuanceUnavailableError(
            "token_issuer_unsupported_mode",
            "The built-in token issuer is unavailable when auth mode is `introspection`.",
        )
