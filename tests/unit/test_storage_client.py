"""Focused unit tests for the vendor-neutral storage client facade."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError
from cortex_common import CortexError, S3Settings
from cortex_storage.client import Boto3ObjectStoreClient


@dataclass(slots=True)
class _FakeS3Client:
    head_error: Exception | None = None
    created_with: list[dict[str, Any]] = field(default_factory=list)
    presigned_urls: list[dict[str, Any]] = field(default_factory=list)

    def head_bucket(self, *, Bucket: str) -> None:
        if self.head_error is not None:
            raise self.head_error

    def create_bucket(self, **kwargs: Any) -> None:
        self.created_with.append(kwargs)

    def generate_presigned_url(
        self,
        operation_name: str,
        *,
        Params: dict[str, Any],
        ExpiresIn: int,
        HttpMethod: str,
    ) -> str:
        self.presigned_urls.append(
            {
                "operation_name": operation_name,
                "params": Params,
                "expires_in": ExpiresIn,
                "http_method": HttpMethod,
            }
        )
        key = Params["Key"]
        bucket = Params["Bucket"]
        return f"http://signed.test/{bucket}/{key}"


def _build_storage_client(
    *,
    region: str = "us-east-1",
    head_error: Exception | None = None,
) -> tuple[Boto3ObjectStoreClient, _FakeS3Client, _FakeS3Client]:
    control_fake = _FakeS3Client(head_error=head_error)
    signing_fake = _FakeS3Client()
    client = cast(Boto3ObjectStoreClient, Boto3ObjectStoreClient.__new__(Boto3ObjectStoreClient))
    client._control_client = cast(Any, control_fake)
    client._signing_client = cast(Any, signing_fake)
    client._settings = S3Settings(CORTEX_S3_REGION=region)
    return client, control_fake, signing_fake


def _missing_bucket_error(code: str = "404") -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "missing"}}, "HeadBucket")


def test_ensure_bucket_noops_when_bucket_exists() -> None:
    client, fake, _signing_fake = _build_storage_client()

    client.ensure_bucket("docs")

    assert fake.created_with == []


def test_ensure_bucket_creates_missing_bucket_in_default_region() -> None:
    client, fake, _signing_fake = _build_storage_client(head_error=_missing_bucket_error())

    client.ensure_bucket("docs")

    assert fake.created_with == [{"Bucket": "docs"}]


def test_ensure_bucket_creates_missing_bucket_with_location_constraint() -> None:
    client, fake, _signing_fake = _build_storage_client(
        region="eu-central-1",
        head_error=_missing_bucket_error("NoSuchBucket"),
    )

    client.ensure_bucket("docs")

    assert fake.created_with == [
        {
            "Bucket": "docs",
            "CreateBucketConfiguration": {"LocationConstraint": "eu-central-1"},
        }
    ]


def test_ensure_bucket_translates_unexpected_client_errors() -> None:
    client, _fake, _signing_fake = _build_storage_client(
        head_error=ClientError({"Error": {"Code": "403", "Message": "forbidden"}}, "HeadBucket")
    )

    with pytest.raises(CortexError) as excinfo:
        client.ensure_bucket("docs")

    assert excinfo.value.code == "storage_provider_error"
    assert excinfo.value.status_code == 502
    assert "403" in excinfo.value.detail


def test_ensure_bucket_translates_endpoint_connection_failures() -> None:
    client, _fake, _signing_fake = _build_storage_client(
        head_error=EndpointConnectionError(endpoint_url="http://127.0.0.1:9000/docs")
    )

    with pytest.raises(CortexError) as excinfo:
        client.ensure_bucket("docs")

    assert excinfo.value.code == "storage_endpoint_unreachable"
    assert excinfo.value.status_code == 503


def test_constructor_uses_public_endpoint_for_presigned_urls() -> None:
    client = Boto3ObjectStoreClient(
        S3Settings(
            CORTEX_S3_ENDPOINT="http://minio:9000",
            CORTEX_S3_PUBLIC_ENDPOINT="http://127.0.0.1:9000",
        )
    )

    assert client._control_client.meta.endpoint_url == "http://minio:9000"
    assert client._signing_client.meta.endpoint_url == "http://127.0.0.1:9000"


def test_single_part_upload_uses_signing_client_endpoint() -> None:
    client, control_fake, signing_fake = _build_storage_client()

    signed = client.create_single_part_upload(
        bucket_name="cortex-local",
        object_key="tenant_demo/obj_demo/README.md",
        content_type="text/markdown",
        expires_in=3600,
    )

    assert control_fake.presigned_urls == []
    assert len(signing_fake.presigned_urls) == 1
    assert signing_fake.presigned_urls[0]["operation_name"] == "put_object"
    assert signed.url == "http://signed.test/cortex-local/tenant_demo/obj_demo/README.md"
    assert signed.headers == {"Content-Type": "text/markdown"}


def test_download_request_uses_signing_client_endpoint() -> None:
    client, control_fake, signing_fake = _build_storage_client()

    signed = client.create_download_request(
        bucket_name="cortex-local",
        object_key="tenant_demo/obj_demo/README.md",
        disposition='attachment; filename="README.md"',
        expires_in=300,
    )

    assert control_fake.presigned_urls == []
    assert len(signing_fake.presigned_urls) == 1
    assert signing_fake.presigned_urls[0]["operation_name"] == "get_object"
    assert signed.url == "http://signed.test/cortex-local/tenant_demo/obj_demo/README.md"
    assert signed.headers == {}
