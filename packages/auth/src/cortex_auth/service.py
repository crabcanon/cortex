"""Authorization service and policy evaluation helpers."""

from __future__ import annotations

from typing import Any

from cortex_common import AuthSettings, new_prefixed_id, utc_now
from cortex_db.uow import CortexUnitOfWork
from cortex_domain import (
    AccessLevel,
    ActorRecord,
    AuthorizationDecisionRecord,
    DecisionEffect,
    PermissionRecord,
    TenantRecord,
)
from cortex_observability import get_trace_context

from .errors import AuthenticationError, AuthorizationDeniedError
from .models import AuthorizationDecision, CallerContext, ResourceAuthorizationContext
from .tokens import TokenValidator, build_token_validator


class AuthorizationService:
    """Authenticate callers and evaluate functional/data permissions."""

    def __init__(
        self,
        settings: AuthSettings,
        token_validator: TokenValidator | None = None,
    ) -> None:
        self._settings = settings
        self._token_validator = token_validator or build_token_validator(settings)

    async def authenticate(self, authorization_header: str | None) -> CallerContext:
        if not authorization_header:
            raise AuthenticationError("Missing Authorization header.", code="missing_authorization")
        scheme, _, token = authorization_header.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise AuthenticationError("Bearer token required.", code="invalid_authorization_scheme")
        return await self._token_validator.validate(token.strip())

    async def authorize(
        self,
        *,
        uow: CortexUnitOfWork,
        caller: CallerContext,
        permission_key: str,
        request_id: str | None = None,
        resource: ResourceAuthorizationContext | None = None,
    ) -> AuthorizationDecision:
        if resource is None:
            decision = AuthorizationDecision(
                effect=DecisionEffect.ALLOW
                if permission_key in caller.scopes
                else DecisionEffect.DENY,
                reason_code="functional_scope_granted"
                if permission_key in caller.scopes
                else "insufficient_scope",
                permission_key=permission_key,
                required_scopes=() if permission_key in caller.scopes else (permission_key,),
            )
            if decision.effect is DecisionEffect.ALLOW:
                try:
                    actor = await self._ensure_actor(uow, caller)
                    await self._ensure_permission_catalog(uow, permission_key, resource)
                    await self._audit_decision(
                        uow=uow,
                        actor=actor,
                        permission_key=permission_key,
                        request_id=request_id,
                        resource=resource,
                        decision=decision,
                    )
                except Exception:
                    return decision
                return decision
            raise AuthorizationDeniedError(
                "Caller is not allowed to perform this action.",
                reason_code=decision.reason_code,
                required_scopes=decision.required_scopes,
            )

        actor = await self._ensure_actor(uow, caller)
        await self._ensure_permission_catalog(uow, permission_key, resource)

        decision = await self._evaluate(
            uow=uow,
            caller=caller,
            actor=actor,
            permission_key=permission_key,
            resource=resource,
        )
        await self._audit_decision(
            uow=uow,
            actor=actor,
            permission_key=permission_key,
            request_id=request_id,
            resource=resource,
            decision=decision,
        )
        if decision.effect is DecisionEffect.DENY:
            raise AuthorizationDeniedError(
                "Caller is not allowed to perform this action.",
                reason_code=decision.reason_code,
                decision_id=decision.decision_id,
                required_scopes=decision.required_scopes,
                required_permissions=decision.required_permissions,
            )
        return decision

    async def _ensure_actor(self, uow: CortexUnitOfWork, caller: CallerContext) -> ActorRecord:
        tenant = await uow.tenants.get(caller.tenant_id)
        if tenant is None:
            if not self._settings.auto_provision_principals:
                raise AuthenticationError("Tenant is not provisioned.", code="tenant_not_found")
            tenant = await uow.tenants.add(
                TenantRecord(
                    tenant_id=caller.tenant_id,
                    tenant_key=caller.tenant_id,
                    display_name=caller.raw_claims.get("tenant_name") or caller.tenant_id,
                    status="active",
                )
            )

        actor_id = caller.actor_id or caller.subject
        actor = await uow.actors.get(actor_id)
        if actor is None and caller.actor_ref:
            actor = await uow.actors.get_by_ref(
                tenant.tenant_id,
                actor_type=caller.actor_type,
                actor_ref=caller.actor_ref,
            )
        if actor is None:
            if not self._settings.auto_provision_principals:
                raise AuthenticationError("Actor is not provisioned.", code="actor_not_found")
            actor = await uow.actors.add(
                ActorRecord(
                    actor_id=actor_id,
                    tenant_id=tenant.tenant_id,
                    actor_type=caller.actor_type,
                    actor_ref=caller.actor_ref or caller.subject,
                    display_name=caller.display_name,
                    metadata={"client_id": caller.client_id} if caller.client_id else {},
                )
            )
        caller.actor_id = actor.actor_id
        return actor

    async def _ensure_permission_catalog(
        self,
        uow: CortexUnitOfWork,
        permission_key: str,
        resource: ResourceAuthorizationContext | None,
    ) -> None:
        if await uow.permissions.get(permission_key) is not None:
            return
        resource_type = resource.resource_type if resource and resource.resource_type else "system"
        action_name = permission_key.split(":")[-1]
        await uow.permissions.add(
            PermissionRecord(
                permission_key=permission_key,
                permission_kind="functional",
                resource_type=resource_type,
                action_name=action_name,
                metadata={"provisioned_by": "cortex_auth"},
            )
        )

    async def _evaluate(
        self,
        *,
        uow: CortexUnitOfWork,
        caller: CallerContext,
        actor: ActorRecord,
        permission_key: str,
        resource: ResourceAuthorizationContext | None,
    ) -> AuthorizationDecision:
        if permission_key not in caller.scopes:
            return AuthorizationDecision(
                effect=DecisionEffect.DENY,
                reason_code="insufficient_scope",
                permission_key=permission_key,
                required_scopes=(permission_key,),
            )

        if resource is None:
            return AuthorizationDecision(
                effect=DecisionEffect.ALLOW,
                reason_code="functional_scope_granted",
                permission_key=permission_key,
            )

        if resource.tenant_id != caller.tenant_id:
            return AuthorizationDecision(
                effect=DecisionEffect.DENY,
                reason_code="cross_tenant_denied",
                permission_key=permission_key,
                required_permissions=(permission_key,),
            )

        access_policy_decision = self._evaluate_access_policy(caller, resource, permission_key)
        if access_policy_decision is not None:
            return access_policy_decision

        if resource.resource_type == "job":
            return AuthorizationDecision(
                effect=DecisionEffect.ALLOW,
                reason_code="job_tenant_boundary_ok",
                permission_key=permission_key,
            )

        if resource.owner_actor_id and actor.actor_id == resource.owner_actor_id:
            return AuthorizationDecision(
                effect=DecisionEffect.ALLOW,
                reason_code="resource_owner",
                permission_key=permission_key,
            )

        role_decision = await self._evaluate_role_bindings(
            uow=uow,
            actor=actor,
            permission_key=permission_key,
            resource=resource,
        )
        if role_decision is not None:
            return role_decision

        policy_decision = await self._evaluate_policies(
            uow=uow,
            caller=caller,
            permission_key=permission_key,
            resource=resource,
        )
        if policy_decision is not None:
            return policy_decision

        if resource.access_level in {None, AccessLevel.TENANT_SHARED}:
            return AuthorizationDecision(
                effect=DecisionEffect.ALLOW,
                reason_code="tenant_shared_access",
                permission_key=permission_key,
            )

        return AuthorizationDecision(
            effect=DecisionEffect.DENY,
            reason_code="resource_access_denied",
            permission_key=permission_key,
            required_permissions=(permission_key,),
        )

    def _evaluate_access_policy(
        self,
        caller: CallerContext,
        resource: ResourceAuthorizationContext,
        permission_key: str,
    ) -> AuthorizationDecision | None:
        policy = resource.access_policy
        if not policy:
            return None

        actor_id = caller.actor_id or caller.subject
        deny_actor_ids = {str(value) for value in policy.get("deny_actor_ids", [])}
        if actor_id in deny_actor_ids:
            return AuthorizationDecision(
                effect=DecisionEffect.DENY,
                reason_code="resource_policy_denied",
                permission_key=permission_key,
                required_permissions=(permission_key,),
            )

        allow_actor_ids = {str(value) for value in policy.get("allow_actor_ids", [])}
        if allow_actor_ids and actor_id in allow_actor_ids:
            return AuthorizationDecision(
                effect=DecisionEffect.ALLOW,
                reason_code="resource_policy_allow",
                permission_key=permission_key,
            )

        owner_actor_id = policy.get("owner_actor_id")
        if owner_actor_id and actor_id == str(owner_actor_id):
            return AuthorizationDecision(
                effect=DecisionEffect.ALLOW,
                reason_code="resource_policy_owner",
                permission_key=permission_key,
            )

        deny_roles = {
            str(value)
            for value in [
                *policy.get("deny_roles", []),
                *policy.get("denied_role_keys", []),
            ]
        }
        if deny_roles and caller.roles.intersection(deny_roles):
            return AuthorizationDecision(
                effect=DecisionEffect.DENY,
                reason_code="resource_policy_denied",
                permission_key=permission_key,
                required_permissions=(permission_key,),
            )

        allow_roles = {
            str(value)
            for value in [
                *policy.get("allow_roles", []),
                *policy.get("allowed_role_keys", []),
            ]
        }
        if allow_roles and caller.roles.intersection(allow_roles):
            return AuthorizationDecision(
                effect=DecisionEffect.ALLOW,
                reason_code="resource_policy_allow",
                permission_key=permission_key,
            )
        return None

    async def _evaluate_role_bindings(
        self,
        *,
        uow: CortexUnitOfWork,
        actor: ActorRecord,
        permission_key: str,
        resource: ResourceAuthorizationContext,
    ) -> AuthorizationDecision | None:
        bindings = await uow.actor_role_bindings.list_for_actor(
            actor.actor_id,
            tenant_id=actor.tenant_id,
            resource_type=resource.resource_type,
            resource_id=resource.resource_id,
            now=utc_now(),
        )
        role_ids = [binding.role_id for binding in bindings]
        if not role_ids:
            return None
        role_permissions = await uow.role_permissions.list_for_role_ids(role_ids)
        effects = {
            role_permission.effect
            for role_permission in role_permissions
            if role_permission.permission_key == permission_key
        }
        if DecisionEffect.DENY in effects:
            return AuthorizationDecision(
                effect=DecisionEffect.DENY,
                reason_code="role_binding_denied",
                permission_key=permission_key,
                required_permissions=(permission_key,),
            )
        if DecisionEffect.ALLOW in effects:
            return AuthorizationDecision(
                effect=DecisionEffect.ALLOW,
                reason_code="role_binding_match",
                permission_key=permission_key,
            )
        return None

    async def _evaluate_policies(
        self,
        *,
        uow: CortexUnitOfWork,
        caller: CallerContext,
        permission_key: str,
        resource: ResourceAuthorizationContext,
    ) -> AuthorizationDecision | None:
        policies = await uow.authorization_policies.list_for_tenant(caller.tenant_id)
        for policy in policies:
            if not self._subject_matches(policy.subject_selector, caller):
                continue
            if not self._resource_matches(policy.resource_selector, resource):
                continue
            if not self._conditions_match(policy.condition, caller, resource):
                continue
            return AuthorizationDecision(
                effect=policy.effect,
                reason_code="policy_match_allow"
                if policy.effect is DecisionEffect.ALLOW
                else "policy_match_deny",
                permission_key=permission_key,
                policy_id=policy.policy_id,
                required_permissions=(
                    (permission_key,) if policy.effect is DecisionEffect.DENY else ()
                ),
            )
        return None

    def _subject_matches(self, selector: dict[str, Any], caller: CallerContext) -> bool:
        if not selector:
            return True
        actor_id = caller.actor_id or caller.subject
        checks = (
            ("subjects", {caller.subject}),
            ("actor_ids", {actor_id}),
            ("actor_refs", {caller.actor_ref} if caller.actor_ref else set()),
            ("roles", set(caller.roles)),
            ("groups", set(caller.groups)),
        )
        for key, available_values in checks:
            expected = {str(value) for value in selector.get(key, [])}
            if expected and not available_values.intersection(expected):
                return False
        return True

    def _resource_matches(
        self,
        selector: dict[str, Any],
        resource: ResourceAuthorizationContext,
    ) -> bool:
        if not selector:
            return True
        if selector.get("tenant_ids") and resource.tenant_id not in {
            str(value) for value in selector["tenant_ids"]
        }:
            return False
        if selector.get("resource_types") and resource.resource_type not in {
            str(value) for value in selector["resource_types"]
        }:
            return False
        if selector.get("resource_ids") and resource.resource_id not in {
            str(value) for value in selector["resource_ids"]
        }:
            return False
        allowed_access_levels = {str(value) for value in selector.get("access_levels", [])}
        if allowed_access_levels and (
            resource.access_level is None
            or resource.access_level.value not in allowed_access_levels
        ):
            return False
        return True

    def _conditions_match(
        self,
        condition: dict[str, Any],
        caller: CallerContext,
        resource: ResourceAuthorizationContext,
    ) -> bool:
        if not condition:
            return True
        for key in ("purposes", "environments", "release_rings"):
            expected = {str(value) for value in condition.get(key, [])}
            if not expected:
                continue
            candidate = caller.raw_claims.get(key[:-1]) or caller.raw_claims.get(key)
            if candidate not in expected:
                return False
        for attr_key, expected_value in condition.get("attributes", {}).items():
            candidate = resource.attributes.get(attr_key, caller.raw_claims.get(attr_key))
            if candidate != expected_value:
                return False
        return True

    async def _audit_decision(
        self,
        *,
        uow: CortexUnitOfWork,
        actor: ActorRecord,
        permission_key: str,
        request_id: str | None,
        resource: ResourceAuthorizationContext | None,
        decision: AuthorizationDecision,
    ) -> None:
        trace_context = get_trace_context()
        stored = await uow.authorization_decisions.add(
            AuthorizationDecisionRecord(
                decision_id=new_prefixed_id("decision"),
                tenant_id=actor.tenant_id,
                actor_id=actor.actor_id,
                permission_key=permission_key,
                effect=decision.effect,
                reason_code=decision.reason_code,
                resource_type=resource.resource_type if resource else None,
                resource_id=resource.resource_id if resource else None,
                policy_id=decision.policy_id,
                trace_id=trace_context.get("trace_id"),
                request_id=request_id,
                metadata={
                    "required_scopes": list(decision.required_scopes),
                    "required_permissions": list(decision.required_permissions),
                },
            )
        )
        decision.decision_id = stored.decision_id
