from typing import BinaryIO, Protocol


class StorageProvider(Protocol):
    """Swappable file storage provider interface (local filesystem in dev)."""

    async def save(self, key: str, file: BinaryIO) -> str:
        ...

    async def read(self, key: str) -> bytes:
        ...
