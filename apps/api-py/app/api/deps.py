from dataclasses import dataclass

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import User
from app.db.session import get_db

settings = get_settings()


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str
    name: str


def get_current_user(db: Session = Depends(get_db)) -> CurrentUser:
    """Single-user local MVP: automatically ensures dev user exists in DB."""
    user = db.execute(select(User).where(User.id == settings.dev_user_id)).scalar_one_or_none()
    if user is None:
        user = User(
            id=settings.dev_user_id,
            email=settings.dev_user_email,
            name=settings.dev_user_name,
        )
        db.add(user)
        db.commit()
    return CurrentUser(id=user.id, email=user.email or "", name=user.name or "")
