from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.core.errors import AppError, app_error_handler

settings = get_settings()

app = FastAPI(title="Cartana API (Python)", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)
app.include_router(api_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "cartana-api-py", "status": "ok"}
