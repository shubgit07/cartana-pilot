from fastapi import APIRouter

from app.api.routes import health, projects

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(projects.router, prefix="/projects")

# Remaining domain routers (sources, chat, requirements, tasks, audit,
# coverage) are included here as each module is migrated, mirroring the
# route paths documented in MIGRATION_STATUS.md.
