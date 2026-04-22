"""Storage orchestration services."""

from __future__ import annotations

import asyncio
import math
import mimetypes
import re
import time
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from cortex_common import (
    CortexError,
    NotFoundError,
    S3Settings,
    ValidationError,
    new_prefixed_id,
    utc_now,
)
from cortex_contracts import (
    AccessPolicy,
    AuditFields,
    DownloadDisposition,
    DownloadUrlResponse,
    StorageObject,
    StorageObjectStatus,
    StorageUploadCompleteRequest,
    StorageUploadCreateRequest,
    StorageUploadSession,
    UploadMode,
    UploadSessionStatus,
)
from cortex_db import CortexUnitOfWork
from cortex_domain import (
    AccessLevel,
    ObjectRecord,
    ObjectStatus,
    ObjectVersionRecord,
    StorageBucketRecord,
)
from cortex_observability import MetricsFacade
from opentelemetry import trace

from .client import Boto3ObjectStoreClient, ObjectStoreClientProtocol

_FILENAME_SANITIZER = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_segment(value: str, *, fallback: str) -> str:
    normalized = _FILENAME_SANITIZER.sub("-", value.strip()).strip("-.")
    return normalized or fallback


class ChecksumService:
    """Validation helpers for object integrity metadata."""

    @staticmethod
    def normalize_sha256(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        if not re.fullmatch(r"[0-9a-f]{64}", normalized):
            raise ValidationError("checksum_sha256 must be a lowercase 64-char SHA-256 hex digest.")
        return normalized

    @classmethod
    def resolve_sha256(cls, *values: str | None) -> str | None:
        normalized = [value for value in (cls.normalize_sha256(raw) for raw in values) if value]
        if not normalized:
            return None
        first = normalized[0]
        if any(value != first for value in normalized[1:]):
            raise ValidationError("checksum_sha256 does not match the initiated upload session.")
        return first


@dataclass(slots=True)
class BucketResolver:
    settings: S3Settings
    object_store: ObjectStoreClientProtocol

    async def resolve(
        self,
        *,
        uow: CortexUnitOfWork,
        tenant_id: str,
    ) -> StorageBucketRecord:
        bucket_name = self.settings.bucket
        bucket = None
        bucket = await uow.buckets.get_by_name(tenant_id, bucket_name)
        if bucket is None:
            default_bucket = await uow.buckets.get_default(tenant_id)
            if default_bucket is not None:
                bucket = default_bucket
        if bucket is None:
            if not self.settings.auto_create_bucket:
                raise NotFoundError(f"Storage bucket `{bucket_name}` was not found.")
            bucket = await uow.buckets.add(
                StorageBucketRecord(
                    bucket_id=new_prefixed_id("bucket"),
                    tenant_id=tenant_id,
                    bucket_name=bucket_name,
                    endpoint_url=self.settings.endpoint,
                    region_name=self.settings.region,
                    provider_hint="s3-compatible",
                    is_default=True,
                )
            )
        if self.settings.auto_create_bucket:
            await asyncio.to_thread(self.object_store.ensure_bucket, bucket.bucket_name)
        return bucket


class StorageService:
    """Persist object metadata and produce direct-to-S3 transfer instructions."""

    def __init__(
        self,
        settings: S3Settings,
        *,
        object_store: ObjectStoreClientProtocol | None = None,
        bucket_resolver: BucketResolver | None = None,
    ) -> None:
        self._settings = settings
        self._object_store = object_store or Boto3ObjectStoreClient(settings)
        self._bucket_resolver = bucket_resolver or BucketResolver(settings, self._object_store)
        self._checksums = ChecksumService()
        self._tracer = trace.get_tracer("cortex.storage")
        self._metrics = MetricsFacade("cortex.storage")

    async def create_upload_session(
        self,
        *,
        uow: CortexUnitOfWork,
        caller: Any,
        request: StorageUploadCreateRequest,
    ) -> StorageUploadSession:
        started = time.perf_counter()
        with self._tracer.start_as_current_span("storage.upload.initialize") as span:
            upload_mode = self._select_upload_mode(request)
            part_size = self._settings.default_part_size_bytes
            content_type = self._resolve_content_type(request)
            bucket = await self._bucket_resolver.resolve(
                uow=uow,
                tenant_id=caller.tenant_id,
            )
            object_id = new_prefixed_id("obj")
            expires_at = utc_now() + timedelta(seconds=self._settings.upload_url_ttl_seconds)
            object_key = self._build_object_key(
                tenant_id=caller.tenant_id,
                object_id=object_id,
                filename=request.filename,
            )
            access_level = self._resolve_access_level(request.access_policy)
            access_policy = self._serialize_access_policy(request.access_policy, access_level)
            checksum_sha256 = self._checksums.normalize_sha256(request.checksum_sha256)
            upload_state: dict[str, Any] = {
                "upload_id": object_id,
                "upload_mode": upload_mode.value,
                "expires_at": expires_at.isoformat(),
                "part_size_bytes": part_size,
                "size_bytes_pending": request.size_bytes is None,
            }
            single_part = None
            multipart_parts = []
            if upload_mode is UploadMode.MULTIPART:
                size_bytes = request.size_bytes
                if size_bytes is None:
                    raise RuntimeError("multipart uploads must provide size_bytes")
                provider_upload_id = await asyncio.to_thread(
                    self._object_store.create_multipart_upload,
                    bucket_name=bucket.bucket_name,
                    object_key=object_key,
                    content_type=content_type,
                    metadata=request.metadata,
                )
                upload_state["provider_upload_id"] = provider_upload_id
                part_count = max(1, math.ceil(size_bytes / part_size))
                multipart_parts = [
                    self._object_store.create_multipart_part_upload(
                        bucket_name=bucket.bucket_name,
                        object_key=object_key,
                        provider_upload_id=provider_upload_id,
                        part_number=part_number,
                        expires_in=self._settings.upload_url_ttl_seconds,
                    )
                    for part_number in range(1, part_count + 1)
                ]
            else:
                single_part = self._object_store.create_single_part_upload(
                    bucket_name=bucket.bucket_name,
                    object_key=object_key,
                    content_type=content_type,
                    expires_in=self._settings.upload_url_ttl_seconds,
                )

            await uow.objects.add(
                ObjectRecord(
                    object_id=object_id,
                    tenant_id=caller.tenant_id,
                    bucket_id=bucket.bucket_id,
                    object_key=object_key,
                    filename=request.filename,
                    content_type=content_type,
                    size_bytes=request.size_bytes or 0,
                    checksum_sha256=checksum_sha256,
                    access_level=access_level,
                    access_policy=access_policy,
                    status=ObjectStatus.PENDING_UPLOAD,
                    metadata=dict(request.metadata),
                    tags=list(request.tags),
                    upload_state=upload_state,
                    created_by=caller.actor_id or caller.subject,
                )
            )
            span.set_attribute("cortex.storage.bucket", bucket.bucket_name)
            span.set_attribute("cortex.storage.object_id", object_id)
            span.set_attribute("cortex.storage.upload_mode", upload_mode.value)
            self._metrics.counter(
                "cortex.storage.upload.sessions",
                description="Created storage upload sessions.",
            ).add(1, {"cortex.storage.upload_mode": upload_mode.value})
            self._metrics.histogram(
                "cortex.storage.upload.initialize.duration",
                unit="ms",
                description="Upload initialization latency.",
            ).record(
                (time.perf_counter() - started) * 1000,
                {"cortex.storage.upload_mode": upload_mode.value},
            )
            return StorageUploadSession(
                upload_id=object_id,
                object_id=object_id,
                status=UploadSessionStatus.PENDING_UPLOAD,
                upload_mode=upload_mode,
                bucket=bucket.bucket_name,
                object_key=object_key,
                expires_at=expires_at,
                part_size_bytes=part_size if upload_mode is UploadMode.MULTIPART else None,
                single_part=single_part,
                multipart_parts=multipart_parts,
            )

    async def complete_upload_session(
        self,
        *,
        uow: CortexUnitOfWork,
        upload_id: str,
        request: StorageUploadCompleteRequest,
    ) -> StorageObject:
        with self._tracer.start_as_current_span("storage.upload.complete") as span:
            stored_object = await uow.objects.get(upload_id)
            if stored_object is None:
                raise NotFoundError(f"Upload session `{upload_id}` was not found.")
            if stored_object.status is not ObjectStatus.PENDING_UPLOAD:
                raise CortexError(
                    code="upload_session_conflict",
                    detail="Upload session is not in `pending_upload` state.",
                    status_code=409,
                )

            upload_state = dict(stored_object.upload_state)
            upload_mode = UploadMode(upload_state.get("upload_mode", UploadMode.SINGLE_PART.value))
            checksum_sha256 = self._checksums.resolve_sha256(
                stored_object.checksum_sha256,
                request.checksum_sha256,
            )
            provider_version_ref = None
            etag = stored_object.etag
            storage_class = stored_object.storage_class
            bucket_name = await self._bucket_name(uow, stored_object.bucket_id)
            if upload_mode is UploadMode.MULTIPART:
                provider_upload_id = str(upload_state.get("provider_upload_id") or "")
                if not provider_upload_id:
                    raise CortexError(
                        code="upload_session_invalid",
                        detail="Multipart upload session is missing provider upload id.",
                        status_code=409,
                    )
                if not request.parts:
                    raise ValidationError("Multipart upload completion requires at least one part.")
                response = await asyncio.to_thread(
                    self._object_store.complete_multipart_upload,
                    bucket_name=bucket_name,
                    object_key=stored_object.object_key,
                    provider_upload_id=provider_upload_id,
                    parts=[
                        {"PartNumber": part.part_number, "ETag": part.etag}
                        for part in request.parts
                    ],
                )
                provider_version_ref = self._coerce_string(response.get("VersionId"))
                etag = self._coerce_string(response.get("ETag"))
                storage_class = self._coerce_string(response.get("StorageClass"))
            else:
                try:
                    response = await asyncio.to_thread(
                        self._object_store.head_object,
                        bucket_name=bucket_name,
                        object_key=stored_object.object_key,
                    )
                except CortexError as exc:
                    provider_error_code = str(exc.extra.get("provider_error_code", ""))
                    if exc.code == "storage_provider_error" and provider_error_code in {
                        "404",
                        "NoSuchKey",
                        "NotFound",
                    }:
                        raise CortexError(
                            code="upload_session_incomplete",
                            detail=(
                                "The uploaded object is not yet visible in object storage. "
                                "Upload the file to the signed URL before calling complete."
                            ),
                            status_code=409,
                        ) from exc
                    raise
                etag = self._coerce_string(response.get("ETag")) or etag
                storage_class = self._coerce_string(response.get("StorageClass")) or storage_class
                detected_content_type = self._coerce_string(response.get("ContentType"))
                actual_size_bytes = self._coerce_int(response.get("ContentLength"))
                if detected_content_type:
                    stored_object.content_type = detected_content_type
                if actual_size_bytes is not None:
                    stored_object.size_bytes = actual_size_bytes

            stored_object.checksum_sha256 = checksum_sha256
            stored_object.etag = etag
            stored_object.storage_class = storage_class
            stored_object.status = ObjectStatus.AVAILABLE
            stored_object.upload_state = {}
            stored_object = await uow.objects.update(stored_object) or stored_object

            latest_version = await uow.object_versions.get_latest(stored_object.object_id)
            next_version_no = 1 if latest_version is None else latest_version.version_no + 1
            version = await uow.object_versions.add(
                ObjectVersionRecord(
                    object_version_id=new_prefixed_id("objver"),
                    object_id=stored_object.object_id,
                    version_no=next_version_no,
                    provider_version_ref=provider_version_ref,
                    size_bytes=stored_object.size_bytes,
                    checksum_sha256=stored_object.checksum_sha256,
                    etag=stored_object.etag,
                )
            )
            span.set_attribute("cortex.storage.object_id", stored_object.object_id)
            return await self._to_storage_object(uow=uow, record=stored_object, version=version)

    async def get_object(
        self,
        *,
        uow: CortexUnitOfWork,
        object_id: str,
    ) -> StorageObject:
        record = await uow.objects.get(object_id)
        if record is None or record.status is ObjectStatus.PENDING_UPLOAD:
            raise NotFoundError(f"Object `{object_id}` was not found.")
        return await self._to_storage_object(uow=uow, record=record)

    async def create_download_url(
        self,
        *,
        uow: CortexUnitOfWork,
        object_id: str,
        ttl_seconds: int,
        disposition: DownloadDisposition,
    ) -> DownloadUrlResponse:
        with self._tracer.start_as_current_span("storage.download.sign_url") as span:
            record = await uow.objects.get(object_id)
            if record is None or record.status is ObjectStatus.PENDING_UPLOAD:
                raise NotFoundError(f"Object `{object_id}` was not found.")
            if record.status is ObjectStatus.DELETED:
                raise NotFoundError(f"Object `{object_id}` was not found.")
            effective_ttl = min(ttl_seconds, self._settings.download_max_ttl_seconds)
            bucket_name = await self._bucket_name(uow, record.bucket_id)
            signed = self._object_store.create_download_request(
                bucket_name=bucket_name,
                object_key=record.object_key,
                disposition=f'{disposition.value}; filename="{record.filename}"',
                expires_in=effective_ttl,
            )
            expires_at = utc_now() + timedelta(seconds=effective_ttl)
            span.set_attribute("cortex.storage.object_id", object_id)
            return DownloadUrlResponse(
                object_id=object_id,
                method=signed.method,
                url=signed.url,
                headers=signed.headers,
                expires_at=expires_at,
            )

    def build_access_context(self, record: ObjectRecord) -> dict[str, Any]:
        policy = self._deserialize_access_policy(record)
        owner_actor_id = policy.owner_actor_id or record.created_by
        return {
            "tenant_id": record.tenant_id,
            "resource_type": "object",
            "resource_id": record.object_id,
            "access_level": record.access_level,
            "access_policy": {
                "owner_actor_id": owner_actor_id,
                "allowed_role_keys": policy.allowed_role_keys,
                "denied_role_keys": policy.denied_role_keys,
                "classification_labels": policy.classification_labels,
                "purpose_tags": policy.purpose_tags,
                "constraints": policy.constraints,
            },
            "owner_actor_id": owner_actor_id,
            "attributes": {
                "classification_labels": policy.classification_labels,
                "purpose_tags": policy.purpose_tags,
                **policy.constraints,
            },
        }

    def _select_upload_mode(self, request: StorageUploadCreateRequest) -> UploadMode:
        if request.size_bytes == 0:
            return UploadMode.SINGLE_PART
        if request.size_bytes is None:
            return UploadMode.SINGLE_PART
        if request.size_bytes > self._settings.multipart_threshold_bytes:
            return UploadMode.MULTIPART
        return UploadMode.SINGLE_PART

    def _build_object_key(
        self,
        *,
        tenant_id: str,
        object_id: str,
        filename: str,
    ) -> str:
        parts = [_sanitize_segment(tenant_id, fallback="tenant")]
        parts.extend([object_id, _sanitize_segment(filename, fallback="object.bin")])
        return "/".join(parts)

    def _resolve_content_type(self, request: StorageUploadCreateRequest) -> str:
        if request.content_type:
            normalized = request.content_type.strip()
            if normalized:
                return normalized
        guessed, _ = mimetypes.guess_type(request.filename)
        return guessed or "application/octet-stream"

    def _resolve_access_level(self, access_policy: AccessPolicy | None) -> AccessLevel:
        if access_policy is None or access_policy.access_level is None:
            return AccessLevel.TENANT_PRIVATE
        return AccessLevel(access_policy.access_level.value)

    def _serialize_access_policy(
        self,
        access_policy: AccessPolicy | None,
        access_level: AccessLevel,
    ) -> dict[str, Any]:
        payload = access_policy.model_dump(mode="json") if access_policy is not None else {}
        payload["access_level"] = access_level.value
        return payload

    def _deserialize_access_policy(self, record: ObjectRecord) -> AccessPolicy:
        payload = dict(record.access_policy)
        payload.setdefault("access_level", record.access_level.value)
        return AccessPolicy.model_validate(payload)

    async def _to_storage_object(
        self,
        *,
        uow: CortexUnitOfWork,
        record: ObjectRecord,
        version: ObjectVersionRecord | None = None,
    ) -> StorageObject:
        latest_version = version or await uow.object_versions.get_latest(record.object_id)
        bucket_name = await self._bucket_name(uow, record.bucket_id)
        return StorageObject(
            object_id=record.object_id,
            current_version_id=latest_version.object_version_id if latest_version else None,
            bucket=bucket_name,
            object_key=record.object_key,
            filename=record.filename,
            content_type=record.content_type,
            size_bytes=record.size_bytes,
            checksum_sha256=record.checksum_sha256,
            etag=record.etag,
            storage_class=record.storage_class,
            metadata={key: str(value) for key, value in record.metadata.items()},
            tags=list(record.tags),
            source_uri=record.source_uri,
            access_policy=self._deserialize_access_policy(record),
            status=StorageObjectStatus(record.status.value),
            audit=AuditFields(
                created_at=record.created_at or utc_now(),
                updated_at=record.updated_at or record.created_at or utc_now(),
                created_by=record.created_by,
            ),
        )

    async def _bucket_name(self, uow: CortexUnitOfWork, bucket_id: str) -> str:
        bucket = await uow.buckets.get(bucket_id)
        if bucket is None:
            raise NotFoundError(f"Storage bucket `{bucket_id}` was not found.")
        return bucket.bucket_name

    @staticmethod
    def _coerce_string(value: Any) -> str | None:
        return str(value) if value is not None else None

    @staticmethod
    def _coerce_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
