"""Runtime dependency helpers."""

from collections.abc import AsyncIterator

from cortex_auth import AuthorizationService
from cortex_common import CortexSettings
from cortex_db import CortexUnitOfWork, SessionFactory
from cortex_storage import StorageService
from fastapi import Request


def get_settings(request: Request) -> CortexSettings:
    return request.app.state.settings  # type: ignore[no-any-return]


def get_session_factory(request: Request) -> SessionFactory:
    return request.app.state.session_factory  # type: ignore[no-any-return]


def get_auth_service(request: Request) -> AuthorizationService:
    return request.app.state.auth_service  # type: ignore[no-any-return]


def get_storage_service(request: Request) -> StorageService:
    return request.app.state.storage_service  # type: ignore[no-any-return]


async def get_uow(request: Request) -> AsyncIterator[CortexUnitOfWork]:
    session_factory = get_session_factory(request)
    async with CortexUnitOfWork(session_factory) as uow:
        yield uow
