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

    def head_bucket(self, *, Bucket: str) -> None:
        if self.head_error is not None:
            raise self.head_error

    def create_bucket(self, **kwargs: Any) -> None:
        self.created_with.append(kwargs)


def _build_storage_client(
    *,
    region: str = "us-east-1",
    head_error: Exception | None = None,
) -> tuple[Boto3ObjectStoreClient, _FakeS3Client]:
    fake = _FakeS3Client(head_error=head_error)
    client = cast(Boto3ObjectStoreClient, Boto3ObjectStoreClient.__new__(Boto3ObjectStoreClient))
    client._client = cast(Any, fake)
    client._settings = S3Settings(CORTEX_S3_REGION=region)
    return client, fake


def _missing_bucket_error(code: str = "404") -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "missing"}}, "HeadBucket")


def test_ensure_bucket_noops_when_bucket_exists() -> None:
    client, fake = _build_storage_client()

    client.ensure_bucket("docs")

    assert fake.created_with == []


def test_ensure_bucket_creates_missing_bucket_in_default_region() -> None:
    client, fake = _build_storage_client(head_error=_missing_bucket_error())

    client.ensure_bucket("docs")

    assert fake.created_with == [{"Bucket": "docs"}]


def test_ensure_bucket_creates_missing_bucket_with_location_constraint() -> None:
    client, fake = _build_storage_client(
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
    client, _fake = _build_storage_client(
        head_error=ClientError({"Error": {"Code": "403", "Message": "forbidden"}}, "HeadBucket")
    )

    with pytest.raises(CortexError) as excinfo:
        client.ensure_bucket("docs")

    assert excinfo.value.code == "storage_provider_error"
    assert excinfo.value.status_code == 502
    assert "403" in excinfo.value.detail


def test_ensure_bucket_translates_endpoint_connection_failures() -> None:
    client, _fake = _build_storage_client(
        head_error=EndpointConnectionError(endpoint_url="http://127.0.0.1:9000/docs")
    )

    with pytest.raises(CortexError) as excinfo:
        client.ensure_bucket("docs")

    assert excinfo.value.code == "storage_endpoint_unreachable"
    assert excinfo.value.status_code == 503
