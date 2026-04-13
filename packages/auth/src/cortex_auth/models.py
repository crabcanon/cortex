"""Identity and authorization models."""

from dataclasses import dataclass, field
from typing import Any

from cortex_domain import AccessLevel, DecisionEffect


@dataclass(slots=True)
class CallerContext:
    subject: str
    tenant_id: str
    scopes: frozenset[str]
    actor_id: str | None = None
    actor_ref: str | None = None
    actor_type: str = "user"
    display_name: str | None = None
    client_id: str | None = None
    roles: frozenset[str] = frozenset()
    groups: frozenset[str] = frozenset()
    token_id: str | None = None
    raw_claims: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ResourceAuthorizationContext:
    tenant_id: str
    resource_type: str | None = None
    resource_id: str | None = None
    access_level: AccessLevel | None = None
    access_policy: dict[str, Any] = field(default_factory=dict)
    owner_actor_id: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AuthorizationDecision:
    effect: DecisionEffect
    reason_code: str
    permission_key: str
    decision_id: str | None = None
    policy_id: str | None = None
    required_scopes: tuple[str, ...] = ()
    required_permissions: tuple[str, ...] = ()
