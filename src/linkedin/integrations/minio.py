from __future__ import annotations

from functools import lru_cache
from io import BytesIO
from typing import Any

try:
    import boto3
    from botocore.client import Config
except ImportError:
    boto3 = None
    Config = None

from linkedin.core.config import settings


def is_minio_configured() -> bool:
    return bool(
        settings.minio_endpoint_url
        and settings.minio_access_key
        and settings.minio_secret_key
    )


@lru_cache
def get_minio_client() -> Any:
    if boto3 is None or Config is None:
        raise RuntimeError("boto3 is not installed. Run `uv sync`.")

    if not is_minio_configured():
        raise RuntimeError(
            "MinIO is not configured. Set MINIO_ENDPOINT_URL, "
            "MINIO_ACCESS_KEY, and MINIO_SECRET_KEY."
        )

    return boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint_url,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
    )


def create_presigned_put_url(
    *,
    bucket: str,
    object_key: str,
    content_type: str,
) -> str:
    return str(
        get_minio_client().generate_presigned_url(
            "put_object",
            Params={
                "Bucket": bucket,
                "Key": object_key,
                "ContentType": content_type,
            },
            ExpiresIn=settings.minio_presigned_url_seconds,
        )
    )


def ensure_minio_bucket() -> None:
    client = get_minio_client()
    try:
        client.head_bucket(Bucket=settings.minio_bucket_name)
    except Exception:
        client.create_bucket(Bucket=settings.minio_bucket_name)


def download_object_bytes(*, bucket: str, object_key: str) -> bytes:
    response = get_minio_client().get_object(Bucket=bucket, Key=object_key)
    with response["Body"] as body:
        return bytes(body.read())


def download_object_stream(*, bucket: str, object_key: str) -> BytesIO:
    return BytesIO(download_object_bytes(bucket=bucket, object_key=object_key))
