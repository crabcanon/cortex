"""S3-compatible object storage facade."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, NoReturn, Protocol

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError
from cortex_common import CortexError, S3Settings
from cortex_contracts import MultipartPartUpload, PresignedRequestDescriptor


class ObjectStoreClientProtocol(Protocol):
    def ensure_bucket(self, bucket_name: str) -> None: ...

    def put_object(
        self,
        *,
        bucket_name: str,
        object_key: str,
        body: bytes,
        content_type: str,
        metadata: dict[str, str],
    ) -> dict[str, Any]: ...

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

    def head_object(
        self,
        *,
        bucket_name: str,
        object_key: str,
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
        self._settings = settings
        self._control_client = self._build_client(config=config, endpoint_url=settings.endpoint)
        signing_endpoint = settings.public_endpoint or settings.endpoint
        if signing_endpoint == settings.endpoint:
            self._signing_client = self._control_client
        else:
            self._signing_client = self._build_client(config=config, endpoint_url=signing_endpoint)

    def _build_client(
        self,
        *,
        config: Config,
        endpoint_url: str,
    ) -> BaseClient:
        return boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=self._settings.region,
            aws_access_key_id=self._settings.access_key,
            aws_secret_access_key=self._settings.secret_key,
            config=config,
        )

    def ensure_bucket(self, bucket_name: str) -> None:
        try:
            self._control_client.head_bucket(Bucket=bucket_name)
            return
        except EndpointConnectionError as exc:
            self._raise_endpoint_unreachable("head_bucket", exc)
        except ClientError as exc:
            error_code = str(exc.response.get("Error", {}).get("Code", ""))
            if error_code not in {"404", "NoSuchBucket", "NotFound"}:
                self._raise_client_error("head_bucket", exc)
        except BotoCoreError as exc:
            self._raise_provider_unavailable("head_bucket", exc)

        params: dict[str, Any] = {"Bucket": bucket_name}
        if self._settings.region != "us-east-1":
            params["CreateBucketConfiguration"] = {
                "LocationConstraint": self._settings.region,
            }
        try:
            self._control_client.create_bucket(**params)
        except EndpointConnectionError as exc:
            self._raise_endpoint_unreachable("create_bucket", exc)
        except ClientError as exc:
            self._raise_client_error("create_bucket", exc)
        except BotoCoreError as exc:
            self._raise_provider_unavailable("create_bucket", exc)

    def create_single_part_upload(
        self,
        *,
        bucket_name: str,
        object_key: str,
        content_type: str,
        expires_in: int,
    ) -> PresignedRequestDescriptor:
        try:
            url = self._signing_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": bucket_name,
                    "Key": object_key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
                HttpMethod="PUT",
            )
        except EndpointConnectionError as exc:
            self._raise_endpoint_unreachable("generate_put_object_url", exc)
        except ClientError as exc:
            self._raise_client_error("generate_put_object_url", exc)
        except BotoCoreError as exc:
            self._raise_provider_unavailable("generate_put_object_url", exc)
        return PresignedRequestDescriptor(
            method="PUT",
            url=url,
            headers={"Content-Type": content_type},
        )

    def put_object(
        self,
        *,
        bucket_name: str,
        object_key: str,
        body: bytes,
        content_type: str,
        metadata: dict[str, str],
    ) -> dict[str, Any]:
        try:
            return self._control_client.put_object(
                Bucket=bucket_name,
                Key=object_key,
                Body=body,
                ContentType=content_type,
                Metadata=metadata,
            )
        except EndpointConnectionError as exc:
            self._raise_endpoint_unreachable("put_object", exc)
        except ClientError as exc:
            self._raise_client_error("put_object", exc)
        except BotoCoreError as exc:
            self._raise_provider_unavailable("put_object", exc)

    def create_multipart_upload(
        self,
        *,
        bucket_name: str,
        object_key: str,
        content_type: str,
        metadata: dict[str, str],
    ) -> str:
        try:
            response = self._control_client.create_multipart_upload(
                Bucket=bucket_name,
                Key=object_key,
                ContentType=content_type,
                Metadata=metadata,
            )
        except EndpointConnectionError as exc:
            self._raise_endpoint_unreachable("create_multipart_upload", exc)
        except ClientError as exc:
            self._raise_client_error("create_multipart_upload", exc)
        except BotoCoreError as exc:
            self._raise_provider_unavailable("create_multipart_upload", exc)
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
        try:
            url = self._signing_client.generate_presigned_url(
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
        except EndpointConnectionError as exc:
            self._raise_endpoint_unreachable("generate_upload_part_url", exc)
        except ClientError as exc:
            self._raise_client_error("generate_upload_part_url", exc)
        except BotoCoreError as exc:
            self._raise_provider_unavailable("generate_upload_part_url", exc)
        return MultipartPartUpload(part_number=part_number, method="PUT", url=url, headers={})

    def complete_multipart_upload(
        self,
        *,
        bucket_name: str,
        object_key: str,
        provider_upload_id: str,
        parts: Sequence[dict[str, Any]],
    ) -> dict[str, Any]:
        try:
            return self._control_client.complete_multipart_upload(
                Bucket=bucket_name,
                Key=object_key,
                UploadId=provider_upload_id,
                MultipartUpload={"Parts": list(parts)},
            )
        except EndpointConnectionError as exc:
            self._raise_endpoint_unreachable("complete_multipart_upload", exc)
        except ClientError as exc:
            self._raise_client_error("complete_multipart_upload", exc)
        except BotoCoreError as exc:
            self._raise_provider_unavailable("complete_multipart_upload", exc)

    def head_object(
        self,
        *,
        bucket_name: str,
        object_key: str,
    ) -> dict[str, Any]:
        try:
            return self._control_client.head_object(
                Bucket=bucket_name,
                Key=object_key,
            )
        except EndpointConnectionError as exc:
            self._raise_endpoint_unreachable("head_object", exc)
        except ClientError as exc:
            self._raise_client_error("head_object", exc)
        except BotoCoreError as exc:
            self._raise_provider_unavailable("head_object", exc)

    def create_download_request(
        self,
        *,
        bucket_name: str,
        object_key: str,
        disposition: str,
        expires_in: int,
    ) -> PresignedRequestDescriptor:
        try:
            url = self._signing_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": bucket_name,
                    "Key": object_key,
                    "ResponseContentDisposition": disposition,
                },
                ExpiresIn=expires_in,
                HttpMethod="GET",
            )
        except EndpointConnectionError as exc:
            self._raise_endpoint_unreachable("generate_get_object_url", exc)
        except ClientError as exc:
            self._raise_client_error("generate_get_object_url", exc)
        except BotoCoreError as exc:
            self._raise_provider_unavailable("generate_get_object_url", exc)
        return PresignedRequestDescriptor(method="GET", url=url, headers={})

    def _raise_endpoint_unreachable(
        self,
        action: str,
        exc: EndpointConnectionError,
    ) -> NoReturn:
        raise CortexError(
            code="storage_endpoint_unreachable",
            detail=(
                "S3-compatible storage endpoint is unreachable for "
                f"`{action}` at `{self._settings.endpoint}`."
            ),
            status_code=503,
        ) from exc

    @staticmethod
    def _raise_client_error(action: str, exc: ClientError) -> NoReturn:
        error = exc.response.get("Error", {})
        error_code = str(error.get("Code", "storage_provider_error"))
        message = str(error.get("Message") or exc)
        raise CortexError(
            code="storage_provider_error",
            detail=(
                f"S3-compatible storage request `{action}` "
                f"failed with `{error_code}`: {message}"
            ),
            status_code=502,
            extra={"provider_error_code": error_code},
        ) from exc

    @staticmethod
    def _raise_provider_unavailable(action: str, exc: BotoCoreError) -> NoReturn:
        raise CortexError(
            code="storage_provider_unavailable",
            detail=f"S3-compatible storage request `{action}` failed before receiving a response.",
            status_code=503,
        ) from exc
