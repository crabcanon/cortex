"""Unit-of-work orchestration for async Cortex persistence."""

from sqlalchemy.ext.asyncio import AsyncSession

from .engine import SessionFactory
from .repositories import (
    ActorRepository,
    ActorRoleBindingRepository,
    AuthorizationDecisionRepository,
    AuthorizationPolicyRepository,
    DatasetItemRepository,
    DatasetRepository,
    DocumentArtifactRepository,
    DocumentChunkRepository,
    DocumentRepository,
    DocumentTagRepository,
    JobEventRepository,
    JobRepository,
    KnowledgeRunRepository,
    ObjectRepository,
    ObjectVersionRepository,
    ParserEngineRepository,
    ParserProfileRepository,
    ParseRunAttemptRepository,
    ParseRunRepository,
    PermissionRepository,
    RolePermissionRepository,
    RoleRepository,
    SearchHitRepository,
    SearchRequestRepository,
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
    def roles(self) -> RoleRepository:
        return RoleRepository(self._require_session())

    @property
    def role_permissions(self) -> RolePermissionRepository:
        return RolePermissionRepository(self._require_session())

    @property
    def actor_role_bindings(self) -> ActorRoleBindingRepository:
        return ActorRoleBindingRepository(self._require_session())

    @property
    def authorization_policies(self) -> AuthorizationPolicyRepository:
        return AuthorizationPolicyRepository(self._require_session())

    @property
    def buckets(self) -> StorageBucketRepository:
        return StorageBucketRepository(self._require_session())

    @property
    def parser_engines(self) -> ParserEngineRepository:
        return ParserEngineRepository(self._require_session())

    @property
    def parser_profiles(self) -> ParserProfileRepository:
        return ParserProfileRepository(self._require_session())

    @property
    def objects(self) -> ObjectRepository:
        return ObjectRepository(self._require_session())

    @property
    def object_versions(self) -> ObjectVersionRepository:
        return ObjectVersionRepository(self._require_session())

    @property
    def documents(self) -> DocumentRepository:
        return DocumentRepository(self._require_session())

    @property
    def document_artifacts(self) -> DocumentArtifactRepository:
        return DocumentArtifactRepository(self._require_session())

    @property
    def document_tags(self) -> DocumentTagRepository:
        return DocumentTagRepository(self._require_session())

    @property
    def document_chunks(self) -> DocumentChunkRepository:
        return DocumentChunkRepository(self._require_session())

    @property
    def datasets(self) -> DatasetRepository:
        return DatasetRepository(self._require_session())

    @property
    def dataset_items(self) -> DatasetItemRepository:
        return DatasetItemRepository(self._require_session())

    @property
    def jobs(self) -> JobRepository:
        return JobRepository(self._require_session())

    @property
    def job_events(self) -> JobEventRepository:
        return JobEventRepository(self._require_session())

    @property
    def parse_runs(self) -> ParseRunRepository:
        return ParseRunRepository(self._require_session())

    @property
    def parse_run_attempts(self) -> ParseRunAttemptRepository:
        return ParseRunAttemptRepository(self._require_session())

    @property
    def knowledge_runs(self) -> KnowledgeRunRepository:
        return KnowledgeRunRepository(self._require_session())

    @property
    def search_requests(self) -> SearchRequestRepository:
        return SearchRequestRepository(self._require_session())

    @property
    def search_hits(self) -> SearchHitRepository:
        return SearchHitRepository(self._require_session())

    @property
    def authorization_decisions(self) -> AuthorizationDecisionRepository:
        return AuthorizationDecisionRepository(self._require_session())
