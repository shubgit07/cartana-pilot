"""File storage providers.

Uploads go through a small swappable interface so the local filesystem (dev)
can be replaced by an object store (AWS S3) without touching the service layer.

Storage keys are *logical* POSIX-style strings such as
``projects/<project_id>/<timestamp>-<safe_filename>``; they are never treated
as filesystem paths. ``LocalStorageProvider`` maps the key's segments onto
``Path`` parts, while ``S3StorageProvider`` maps them directly to S3 object keys.
"""
from __future__ import annotations

import logging
import re
import time
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

import boto3  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from app.config import get_settings

logger = logging.getLogger(__name__)

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")
_MAX_FILENAME_LENGTH = 200


def safe_filename(filename: str) -> str:
    """Reduce a user supplied filename to a single safe key segment.

    Windows clients may send a full path, so both separators are normalised
    away before the remaining characters are restricted to ``[A-Za-z0-9._-]``.
    """
    basename = PurePosixPath(filename.replace("\\", "/")).name
    cleaned = _UNSAFE_CHARS.sub("_", basename).lstrip(".")
    return (cleaned or "upload.bin")[:_MAX_FILENAME_LENGTH]


def build_storage_key(project_id: str, filename: str) -> str:
    """Build the logical key for a newly uploaded file."""
    timestamp_ms = time.time_ns() // 1_000_000
    return f"projects/{project_id}/{timestamp_ms}-{safe_filename(filename)}"


class StorageProvider(Protocol):
    """Swappable file storage provider interface."""

    def save(self, key: str, data: bytes) -> str:
        """Persist ``data`` under ``key`` and return the stored key."""
        ...

    def read(self, key: str) -> bytes:
        """Return the bytes stored under ``key``."""
        ...

    def remove(self, key: str) -> None:
        """Delete ``key``; a missing object is not an error."""
        ...


class LocalStorageProvider:
    """Stores files on the local filesystem under ``storage_local_root``."""

    def __init__(self, root: str | Path | None = None) -> None:
        configured = root if root is not None else get_settings().storage_local_root
        self.root = Path(configured).expanduser().resolve()

    def path_for(self, key: str) -> Path:
        """Translate a logical key into a filesystem path inside the root."""
        parts = [part for part in PurePosixPath(key).parts if part not in ("", ".", "/")]
        if not parts or any(part == ".." for part in parts):
            raise ValueError(f"Invalid storage key: {key!r}")

        path = self.root.joinpath(*parts)
        if self.root not in path.resolve().parents:
            raise ValueError(f"Invalid storage key: {key!r}")
        return path

    def save(self, key: str, data: bytes) -> str:
        path = self.path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def read(self, key: str) -> bytes:
        return self.path_for(key).read_bytes()

    def remove(self, key: str) -> None:
        self.path_for(key).unlink(missing_ok=True)


class S3StorageProvider:
    """Stores files in an AWS S3 bucket."""

    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        endpoint_url: str | None = None,
    ) -> None:
        self.bucket = bucket
        self.region = region

        client_kwargs: dict[str, Any] = {"region_name": region}
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
        if aws_access_key_id and aws_secret_access_key:
            client_kwargs["aws_access_key_id"] = aws_access_key_id
            client_kwargs["aws_secret_access_key"] = aws_secret_access_key

        self.client = boto3.client("s3", **client_kwargs)

    def save(self, key: str, data: bytes) -> str:
        """Upload bytes to S3 under ``key``."""
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ServerSideEncryption="AES256",
            )
            return key
        except Exception as e:
            logger.error("Failed to save object to S3 (bucket=%s, key=%s): %s", self.bucket, key, e)
            raise

    def read(self, key: str) -> bytes:
        """Download bytes from S3 under ``key``."""
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("NoSuchKey", "404", "NoSuchBucket"):
                raise FileNotFoundError(f"Key {key!r} not found in bucket {self.bucket!r}") from e
            logger.error("Failed to read object from S3 (bucket=%s, key=%s): %s", self.bucket, key, e)
            raise

    def remove(self, key: str) -> None:
        """Delete object from S3 under ``key``."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code not in ("NoSuchKey", "404"):
                logger.warning("Failed to delete object from S3 (bucket=%s, key=%s): %s", self.bucket, key, e)


@lru_cache(maxsize=1)
def get_storage() -> StorageProvider:
    """Return the storage provider selected by configuration."""
    settings = get_settings()
    driver = (settings.storage_driver or "local").lower()
    if driver == "local":
        return LocalStorageProvider(settings.storage_local_root)
    if driver == "s3":
        if not settings.aws_s3_bucket_name:
            raise ValueError("AWS_S3_BUCKET_NAME must be configured when STORAGE_DRIVER=s3")
        return S3StorageProvider(
            bucket=settings.aws_s3_bucket_name,
            region=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            endpoint_url=settings.aws_s3_endpoint_url,
        )
    raise ValueError(f"Unsupported storage driver: {settings.storage_driver}")
