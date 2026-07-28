from fastapi import APIRouter

from app.api.routes import health, projects, sources

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(projects.router, prefix="/projects")
api_router.include_router(sources.router, prefix="/projects/{project_id}/sources")

# Remaining domain routers (chat, requirements, tasks, coverage, audit) are
# included here as each module is migrated, mirroring the route paths
# documented in MIGRATION_STATUS.md.
