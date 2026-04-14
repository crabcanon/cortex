"""S3-compatible object storage facade."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import ClientError
from cortex_common import S3Settings
from cortex_contracts import MultipartPartUpload, PresignedRequestDescriptor


class ObjectStoreClientProtocol(Protocol):
    def ensure_bucket(self, bucket_name: str) -> None: ...

    def create_single_part_upload(
        self,
        *,
        bucket_name: str,
        object_key: str,
        content_type: str,
        expires_in: int,
    ) -> PresignedRequestDescriptor: ...

    def create_multipart_upload(
        self,
        *,
        bucket_name: str,
        object_key: str,
        content_type: str,
        metadata: dict[str, str],
    ) -> str: ...

    def create_multipart_part_upload(
        self,
        *,
        bucket_name: str,
        object_key: str,
        provider_upload_id: str,
        part_number: int,
        expires_in: int,
    ) -> MultipartPartUpload: ...

    def complete_multipart_upload(
        self,
        *,
        bucket_name: str,
        object_key: str,
        provider_upload_id: str,
        parts: Sequence[dict[str, Any]],
    ) -> dict[str, Any]: ...

    def create_download_request(
        self,
        *,
        bucket_name: str,
        object_key: str,
        disposition: str,
        expires_in: int,
    ) -> PresignedRequestDescriptor: ...


class Boto3ObjectStoreClient:
    """Vendor-neutral S3-compatible facade backed by boto3."""

    def __init__(self, settings: S3Settings) -> None:
        addressing_style = "path" if settings.force_path_style else "auto"
        config = Config(signature_version="s3v4", s3={"addressing_style": addressing_style})
        self._client: BaseClient = boto3.client(
            "s3",
            endpoint_url=settings.endpoint,
            region_name=settings.region,
            aws_access_key_id=settings.access_key,
            aws_secret_access_key=settings.secret_key,
            config=config,
        )
        self._settings = settings

    def ensure_bucket(self, bucket_name: str) -> None:
        try:
            self._client.head_bucket(Bucket=bucket_name)
            return
        except ClientError as exc:
            error_code = str(exc.response.get("Error", {}).get("Code", ""))
            if error_code not in {"404", "NoSuchBucket", "NotFound"}:
                raise

        params: dict[str, Any] = {"Bucket": bucket_name}
        if self._settings.region != "us-east-1":
            params["CreateBucketConfiguration"] = {
                "LocationConstraint": self._settings.region,
            }
        self._client.create_bucket(**params)

    def create_single_part_upload(
        self,
        *,
        bucket_name: str,
        object_key: str,
        content_type: str,
        expires_in: int,
    ) -> PresignedRequestDescriptor:
        url = self._client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": bucket_name,
                "Key": object_key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in,
            HttpMethod="PUT",
        )
        return PresignedRequestDescriptor(
            method="PUT",
            url=url,
            headers={"Content-Type": content_type},
        )

    def create_multipart_upload(
        self,
        *,
        bucket_name: str,
        object_key: str,
        content_type: str,
        metadata: dict[str, str],
    ) -> str:
        response = self._client.create_multipart_upload(
            Bucket=bucket_name,
            Key=object_key,
            ContentType=content_type,
            Metadata=metadata,
        )
        upload_id = response.get("UploadId")
        if not isinstance(upload_id, str) or not upload_id:
            raise RuntimeError("S3-compatible provider did not return UploadId.")
        return upload_id

    def create_multipart_part_upload(
        self,
        *,
        bucket_name: str,
        object_key: str,
        provider_upload_id: str,
        part_number: int,
        expires_in: int,
    ) -> MultipartPartUpload:
        url = self._client.generate_presigned_url(
            "upload_part",
            Params={
                "Bucket": bucket_name,
                "Key": object_key,
                "UploadId": provider_upload_id,
                "PartNumber": part_number,
            },
            ExpiresIn=expires_in,
            HttpMethod="PUT",
        )
        return MultipartPartUpload(part_number=part_number, method="PUT", url=url, headers={})

    def complete_multipart_upload(
        self,
        *,
        bucket_name: str,
        object_key: str,
        provider_upload_id: str,
        parts: Sequence[dict[str, Any]],
    ) -> dict[str, Any]:
        return self._client.complete_multipart_upload(
            Bucket=bucket_name,
            Key=object_key,
            UploadId=provider_upload_id,
            MultipartUpload={"Parts": list(parts)},
        )

    def create_download_request(
        self,
        *,
        bucket_name: str,
        object_key: str,
        disposition: str,
        expires_in: int,
    ) -> PresignedRequestDescriptor:
        url = self._client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": bucket_name,
                "Key": object_key,
                "ResponseContentDisposition": disposition,
            },
            ExpiresIn=expires_in,
            HttpMethod="GET",
        )
        return PresignedRequestDescriptor(method="GET", url=url, headers={})
