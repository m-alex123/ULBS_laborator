from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_session_token, verify_password
from app.db.models import User
from app.db.session import get_db
from app.web.deps import get_current_user, require_admin, templates

router = APIRouter(tags=["auth"])


def _is_secure_cookie() -> bool:
    return settings.ENVIRONMENT.lower() == "production"


def _login_context(error: str | None = None, email: str = "") -> dict[str, object]:
    return {
        "error": error,
        "email": email,
        "show_demo_shortcuts": settings.ENVIRONMENT.lower() != "production",
        "seed_user_email": settings.SEED_USER_EMAIL,
        "seed_user_password": settings.SEED_USER_PASSWORD,
        "seed_admin_email": settings.SEED_ADMIN_EMAIL,
        "seed_admin_password": settings.SEED_ADMIN_PASSWORD,
    }


@router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    current_user: User | None = Depends(get_current_user),
):
    """Render DS-01 Login screen or redirect if already authenticated."""
    if current_user:
        return RedirectResponse(url="/watchlist", status_code=303)
    return templates.TemplateResponse(request, "login.html", _login_context())


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Authenticate email/password via bcrypt and issue an HttpOnly signed session cookie."""
    normalized_email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized_email))
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request,
            "login.html",
            _login_context(error="Email sau parolă incorectă.", email=email),
            status_code=401,
        )

    token = create_session_token(
        user_id=user.id,
        role=user.role,
        secret_key=settings.SECRET_KEY,
        expires_in_seconds=settings.SESSION_MAX_AGE_SECONDS,
    )
    response = RedirectResponse(url="/watchlist", status_code=303)
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=_is_secure_cookie(),
        path="/",
    )
    return response


@router.post("/logout")
def logout() -> RedirectResponse:
    """Clear the signed session cookie and redirect to /login."""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key=settings.SESSION_COOKIE_NAME, path="/")
    return response


@router.get("/admin/status")
def admin_status(admin_user: User = Depends(require_admin)) -> dict[str, str]:
    """Role-protected endpoint verifying admin authorization."""
    return {
        "status": "ok",
        "admin_email": admin_user.email,
        "role": admin_user.role,
    }
