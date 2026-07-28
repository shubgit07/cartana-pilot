"""Serialization helpers shared by the API DTOs.

Kept in one place so every module renders timestamps and enums the same way
the Node backend does - the frontend parses both backends interchangeably
during the migration.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum


def to_iso8601(value: datetime) -> str:
    """Render a timestamp exactly like JavaScript's ``Date.toISOString()``.

    Timestamps are stored as naive UTC values (Prisma ``timestamp(3)``), so a
    naive value is treated as UTC and formatted with millisecond precision and
    a trailing ``Z``.
    """
    moment = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    moment = moment.astimezone(timezone.utc)
    return f"{moment.strftime('%Y-%m-%dT%H:%M:%S')}.{moment.microsecond // 1000:03d}Z"


def enum_value(value: object) -> str:
    """Return the wire value of an enum column (already a str when raw)."""
    return value.value if isinstance(value, Enum) else str(value)
