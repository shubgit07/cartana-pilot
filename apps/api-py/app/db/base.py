from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models.

    Concrete models mirroring apps/api/prisma/schema.prisma (User, Project,
    Source, Chunk, Requirement, RequirementChunk, Task, TaskChunk,
    CoverageLink, AuditRun, AuditFinding) live in app/db/models.py.
    """
