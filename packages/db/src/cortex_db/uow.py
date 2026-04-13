"""Unit-of-work orchestration for async Cortex persistence."""

from sqlalchemy.ext.asyncio import AsyncSession

from .engine import SessionFactory
from .repositories import (
    ActorRepository,
    AuthorizationDecisionRepository,
    DatasetRepository,
    DocumentRepository,
    JobRepository,
    ObjectRepository,
    PermissionRepository,
    StorageBucketRepository,
    TenantRepository,
)


class CortexUnitOfWork:
    """Coordinate repositories against a shared async transaction."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> "CortexUnitOfWork":
        self.session = self._session_factory()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.session is None:
            return
        try:
            if exc is None:
                await self.session.commit()
            else:
                await self.session.rollback()
        finally:
            await self.session.close()
            self.session = None

    async def commit(self) -> None:
        if self.session is None:
            raise RuntimeError("unit of work is not active")
        await self.session.commit()

    async def rollback(self) -> None:
        if self.session is None:
            raise RuntimeError("unit of work is not active")
        await self.session.rollback()

    def _require_session(self) -> AsyncSession:
        if self.session is None:
            raise RuntimeError("unit of work is not active")
        return self.session

    @property
    def tenants(self) -> TenantRepository:
        return TenantRepository(self._require_session())

    @property
    def actors(self) -> ActorRepository:
        return ActorRepository(self._require_session())

    @property
    def permissions(self) -> PermissionRepository:
        return PermissionRepository(self._require_session())

    @property
    def buckets(self) -> StorageBucketRepository:
        return StorageBucketRepository(self._require_session())

    @property
    def objects(self) -> ObjectRepository:
        return ObjectRepository(self._require_session())

    @property
    def documents(self) -> DocumentRepository:
        return DocumentRepository(self._require_session())

    @property
    def datasets(self) -> DatasetRepository:
        return DatasetRepository(self._require_session())

    @property
    def jobs(self) -> JobRepository:
        return JobRepository(self._require_session())

    @property
    def authorization_decisions(self) -> AuthorizationDecisionRepository:
        return AuthorizationDecisionRepository(self._require_session())
