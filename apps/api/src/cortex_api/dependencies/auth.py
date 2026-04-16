"""Authentication dependencies."""

from typing import Annotated

from cortex_auth import AuthorizationService, CallerContext
from cortex_contracts import X_CORTEX_ISSUER_SECRET_HEADER
from fastapi import Depends, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from .runtime import get_auth_service

bearer_auth_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description="Bearer access token for protected Cortex APIs.",
)
bootstrap_issuer_secret_header = APIKeyHeader(
    name=X_CORTEX_ISSUER_SECRET_HEADER,
    auto_error=False,
    scheme_name="BootstrapIssuerSecret",
)


async def get_current_caller(
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_auth_scheme)],
) -> CallerContext:
    authorization = None
    if credentials is not None:
        authorization = f"{credentials.scheme} {credentials.credentials}"
    return await auth_service.authenticate(authorization)


async def get_bootstrap_issuer_secret(
    issuer_secret: Annotated[str | None, Security(bootstrap_issuer_secret_header)],
) -> str | None:
    return issuer_secret
