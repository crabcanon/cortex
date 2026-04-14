"""Storage API DTOs."""

from datetime import datetime

from pydantic import BaseModel, Field

from .enums import (
    StorageObjectStatus,
    UploadMode,
    UploadSessionStatus,
)
from .resources import AccessPolicy, AuditFields


class PresignedRequestDescriptor(BaseModel):
    method: str
    url: str
    headers: dict[str, str] = Field(default_factory=dict)


class MultipartPartUpload(BaseModel):
    part_number: int = Field(ge=1)
    method: str
    url: str
    headers: dict[str, str] = Field(default_factory=dict)


class StorageUploadCreateRequest(BaseModel):
    filename: str
    content_type: str
    size_bytes: int = Field(ge=0)
    checksum_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    metadata: dict[str, str] = Field(default_factory=dict)
    access_policy: AccessPolicy | None = None
    tags: list[str] = Field(default_factory=list)
    upload_mode: UploadMode = UploadMode.SINGLE_PART
    part_size_bytes: int = Field(default=8_388_608, ge=5_242_880)
    bucket_ref: str | None = None
    object_prefix: str | None = None


class StorageUploadSession(BaseModel):
    upload_id: str
    object_id: str
    status: UploadSessionStatus
    upload_mode: UploadMode
    bucket: str | None = None
    object_key: str | None = None
    expires_at: datetime
    part_size_bytes: int | None = None
    single_part: PresignedRequestDescriptor | None = None
    multipart_parts: list[MultipartPartUpload] = Field(default_factory=list)


class CompletedUploadPart(BaseModel):
    part_number: int = Field(ge=1)
    etag: str


class StorageUploadCompleteRequest(BaseModel):
    parts: list[CompletedUploadPart] = Field(default_factory=list)
    checksum_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class StorageObject(BaseModel):
    object_id: str
    filename: str
    content_type: str
    size_bytes: int = Field(ge=0)
    status: StorageObjectStatus
    audit: AuditFields
    current_version_id: str | None = None
    bucket: str | None = None
    object_key: str | None = None
    checksum_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    etag: str | None = None
    storage_class: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    source_uri: str | None = None
    access_policy: AccessPolicy | None = None


class DownloadUrlResponse(BaseModel):
    object_id: str
    method: str
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    expires_at: datetime
