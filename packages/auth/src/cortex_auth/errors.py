"""Authentication and authorization errors."""

from collections.abc import Mapping
from typing import Any

from cortex_common.exceptions import CortexError


class AuthenticationError(CortexError):
    """Raised when the caller cannot be authenticated."""

    def __init__(
        self,
        detail: str,
        *,
        code: str = "authentication_failed",
        extra: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(code, detail, 401, extra or {})


class AuthorizationDeniedError(CortexError):
    """Raised when an authenticated caller lacks required permissions."""

    def __init__(
        self,
        detail: str,
        *,
        reason_code: str,
        decision_id: str | None = None,
        required_scopes: tuple[str, ...] = (),
        required_permissions: tuple[str, ...] = (),
        extra: Mapping[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = dict(extra or {})
        payload["reason_code"] = reason_code
        if decision_id is not None:
            payload["decision_id"] = decision_id
        if required_scopes:
            payload["required_scopes"] = list(required_scopes)
        if required_permissions:
            payload["required_permissions"] = list(required_permissions)
        super().__init__("authorization_denied", detail, 403, payload)
