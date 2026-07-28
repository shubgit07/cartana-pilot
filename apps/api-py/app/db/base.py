from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models.

    Domain models (User, Project, Source, Chunk, Requirement,
    RequirementChunk, Task, TaskChunk, CoverageLink, AuditRun,
    AuditFinding) mirroring apps/api/prisma/schema.prisma are added in the
    schema migration step, which requires explicit sign-off first.
    """
