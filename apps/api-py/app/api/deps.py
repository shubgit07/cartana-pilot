from dataclasses import dataclass

from app.config import get_settings

settings = get_settings()


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str
    name: str


def get_current_user() -> CurrentUser:
    """Single-user local MVP: no real auth yet.

    Mirrors the Node backend's dev-user middleware. Every project-scoped
    query should be filtered by this user id, matching the Node behavior.
    """
    return CurrentUser(id=settings.dev_user_id, email=settings.dev_user_email, name=settings.dev_user_name)
