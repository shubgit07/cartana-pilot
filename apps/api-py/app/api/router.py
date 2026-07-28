from fastapi import APIRouter

from app.api.routes import audit, chat, health, projects, requirements, sources, tasks

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(projects.router, prefix="/projects")
api_router.include_router(sources.router, prefix="/projects/{project_id}/sources")
api_router.include_router(chat.router, prefix="/projects/{project_id}/chat")
api_router.include_router(requirements.router, prefix="/projects/{project_id}/requirements")
api_router.include_router(tasks.router, prefix="/projects/{project_id}/tasks")
api_router.include_router(audit.audit_router, prefix="/projects/{project_id}/audit")
api_router.include_router(audit.coverage_router, prefix="/projects/{project_id}/coverage")
