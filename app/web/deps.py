from collections.abc import Generator
from pathlib import Path
from urllib.parse import urlparse

from fastapi import Depends, HTTPException, Request, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_csrf_token, decode_session_token, verify_csrf_token
from app.db.models import User
from app.db.session import get_db
from app.scraping.polite_client import PoliteHttpClient

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
CSRF_COOKIE_NAME = "p23_csrf"


def is_secure_cookie_env() -> bool:
    """Enable Secure cookies for all non-local environments."""
    return settings.ENVIRONMENT.strip().lower() not in {"development", "dev", "test", "local"}


def set_csrf_cookie(response: Response, token: str) -> None:
    """Set the double-submit CSRF cookie with consistent security flags."""
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        httponly=False,
        samesite="lax",
        secure=is_secure_cookie_env(),
        path="/",
    )


def ensure_csrf_cookie(request: Request, response: Response, csrf_token: str) -> None:
    """Ensure the browser has a CSRF cookie matching the rendered form token."""
    if CSRF_COOKIE_NAME not in request.cookies:
        set_csrf_cookie(response, csrf_token)


def resolve_csrf_token(request: Request) -> str:
    """Reuse existing valid CSRF cookie token or issue a fresh signed token."""
    existing = request.cookies.get(CSRF_COOKIE_NAME)
    if existing and verify_csrf_token(existing, settings.SECRET_KEY):
        return existing
    return create_csrf_token(settings.SECRET_KEY)


def set_session_cookie(response: Response, token: str) -> None:
    """Attach the signed HttpOnly session cookie to an auth response."""
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=is_secure_cookie_env(),
        path="/",
    )


def get_polite_client() -> Generator[PoliteHttpClient, None, None]:
    """Provide a PoliteHttpClient instance (overridable in FastAPI tests)."""
    client = PoliteHttpClient()
    try:
        yield client
    finally:
        client.close()


def verify_csrf_request(request: Request, form_csrf_token: str | None = None) -> None:
    """Enforce CSRF defenses on state-changing POST routes."""
    fetch_site = (request.headers.get("sec-fetch-site") or "").strip().lower()
    if fetch_site == "cross-site":
        raise HTTPException(status_code=403, detail="Cross-site request rejected")

    expected_host = request.url.netloc.lower()
    for header_name in ("origin", "referer"):
        header_val = request.headers.get(header_name)
        if header_val:
            parsed = urlparse(header_val)
            if parsed.netloc and parsed.netloc.lower() != expected_host:
                raise HTTPException(status_code=403, detail="CSRF origin mismatch")

    cookie_csrf = request.cookies.get(CSRF_COOKIE_NAME)
    if cookie_csrf is not None:
        if (
            not form_csrf_token
            or form_csrf_token != cookie_csrf
            or not verify_csrf_token(cookie_csrf, settings.SECRET_KEY)
        ):
            raise HTTPException(status_code=403, detail="CSRF token invalid")


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
    if not user or payload["role"] != user.role:
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
