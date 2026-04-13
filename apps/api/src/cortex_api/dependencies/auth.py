"""Authentication dependencies."""

from typing import Annotated

from cortex_auth import AuthorizationService, CallerContext
from fastapi import Depends, Header

from .runtime import get_auth_service


async def get_current_caller(
    auth_service: Annotated[AuthorizationService, Depends(get_auth_service)],
    authorization: str | None = Header(default=None),
) -> CallerContext:
    return await auth_service.authenticate(authorization)
