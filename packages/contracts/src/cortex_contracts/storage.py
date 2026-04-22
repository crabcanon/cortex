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
    filename: str = Field(
        description="Required original filename presented to storage and downstream parsers.",
        examples=["product-overview.md"],
    )
    content_type: str | None = Field(
        default=None,
        description=(
            "Optional MIME type of the uploaded object. Best default: omit and let Cortex infer "
            "it from `filename`, then reconcile it with the object store during completion."
        ),
        examples=["text/markdown"],
    )
    size_bytes: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Optional total size of the upload in bytes. Best default: omit when unknown before "
            "upload; provide it when the client already knows the file size so Cortex can choose "
            "single-part vs multipart more accurately."
        ),
        examples=[20480],
    )
    checksum_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
        description=(
            "Optional SHA-256 checksum for integrity "
            "verification. Best default: omit if the client "
            "cannot compute it."
        ),
        examples=["a" * 64],
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Optional metadata stored alongside the object. Best default: empty object.",
        examples=[{"source": "swagger-demo", "document_type": "guide"}],
    )
    access_policy: AccessPolicy | None = Field(
        default=None,
        description="Optional access policy attached to the stored object. Best default: omit.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Optional tags used for filtering or governance. Best default: empty list.",
        examples=[["docs", "product"]],
    )


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
    part_number: int = Field(
        ge=1,
        description="Multipart part number exactly as returned during upload session creation.",
        examples=[1],
    )
    etag: str = Field(
        description="ETag returned by the object store after uploading the part.",
        examples=['"part-1-etag"'],
    )


class StorageUploadCompleteRequest(BaseModel):
    parts: list[CompletedUploadPart] = Field(
        default_factory=list,
        description=(
            "Multipart parts to finalize. Best default: empty list for single-part uploads."
        ),
        examples=[[{"part_number": 1, "etag": '"part-1-etag"'}]],
    )
    checksum_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
        description=(
            "Optional final SHA-256 checksum. Best default: "
            "omit unless the client validated the file digest."
        ),
        examples=["b" * 64],
    )


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
