from pathlib import Path

from fastapi import Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_session_token
from app.db.models import User
from app.db.session import get_db

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User | None:
    """Resolve the currently authenticated User from the signed session cookie."""
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        return None
    payload = decode_session_token(token, settings.SECRET_KEY)
    if not payload:
        return None
    user = db.get(User, payload["user_id"])
    if not user:
        return None
    return user


def require_user(
    current_user: User | None = Depends(get_current_user),
) -> User:
    """Redirect unauthenticated SSR requests to /login."""
    if not current_user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return current_user


def require_admin(
    current_user: User | None = Depends(get_current_user),
) -> User:
    """Enforce authentication (401) and admin role (403) server-side."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return current_user
