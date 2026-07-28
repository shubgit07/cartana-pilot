"""File storage providers.

Uploads go through a small swappable interface so the local filesystem (dev)
can later be replaced by an object store without touching the service layer.

Storage keys are *logical* POSIX-style strings such as
``projects/<project_id>/<timestamp>-<safe_filename>``; they are never treated
as filesystem paths. ``LocalStorageProvider`` maps the key's segments onto
``Path`` parts, so a key written on Linux resolves correctly on Windows and
vice versa.
"""
from __future__ import annotations

import re
import time
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Protocol

from app.config import get_settings

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
    """Swappable file storage provider interface (local filesystem in dev)."""

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


@lru_cache(maxsize=1)
def get_storage() -> StorageProvider:
    """Return the storage provider selected by configuration."""
    settings = get_settings()
    driver = (settings.storage_driver or "local").lower()
    if driver == "local":
        return LocalStorageProvider(settings.storage_local_root)
    raise ValueError(f"Unsupported storage driver: {settings.storage_driver}")
