from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_session_token,
    hash_password,
    verify_password,
)
from app.db.models import User
from app.db.session import get_db
from app.web.deps import (
    get_current_user,
    is_secure_cookie_env,
    require_admin,
    resolve_csrf_token,
    set_csrf_cookie,
    set_session_cookie,
    templates,
    verify_csrf_request,
)

router = APIRouter(tags=["auth"])
_DUMMY_BCRYPT_HASH = hash_password("dummy-timing-equalizer-password-only")


def _login_context(
    csrf_token: str,
    error: str | None = None,
    email: str = "",
) -> dict[str, object]:
    show_demo = settings.ENVIRONMENT.strip().lower() not in {"production", "prod", "staging"}
    ctx: dict[str, object] = {
        "error": error,
        "email": email,
        "csrf_token": csrf_token,
        "show_demo_shortcuts": show_demo,
        "is_auth_page": True,
    }
    if show_demo:
        ctx.update(
            {
                "seed_user_email": settings.SEED_USER_EMAIL,
                "seed_user_password": settings.SEED_USER_PASSWORD,
                "seed_admin_email": settings.SEED_ADMIN_EMAIL,
                "seed_admin_password": settings.SEED_ADMIN_PASSWORD,
            }
        )
    return ctx


@router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    current_user: User | None = Depends(get_current_user),
):
    """Render DS-01 Login screen or redirect if already authenticated."""
    if current_user:
        return RedirectResponse(url="/watchlist", status_code=303)
    csrf_token = resolve_csrf_token(request)
    response = templates.TemplateResponse(
        request,
        "login.html",
        _login_context(csrf_token=csrf_token),
    )
    set_csrf_cookie(response, csrf_token)
    return response


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    """Authenticate email/password via bcrypt and issue an HttpOnly signed session cookie."""
    verify_csrf_request(request, csrf_token)

    normalized_email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized_email))
    candidate_hash = user.password_hash if user else _DUMMY_BCRYPT_HASH
    password_ok = verify_password(password, candidate_hash)

    if not user or not password_ok:
        fresh_csrf = resolve_csrf_token(request)
        response = templates.TemplateResponse(
            request,
            "login.html",
            _login_context(
                csrf_token=fresh_csrf,
                error="Email sau parolă incorectă.",
                email=email,
            ),
            status_code=401,
        )
        set_csrf_cookie(response, fresh_csrf)
        return response

    token = create_session_token(
        user_id=user.id,
        role=user.role,
        secret_key=settings.SECRET_KEY,
        expires_in_seconds=settings.SESSION_MAX_AGE_SECONDS,
    )
    response = RedirectResponse(url="/watchlist", status_code=303)
    set_session_cookie(response, token)
    return response


@router.get("/register", response_class=HTMLResponse)
def register_page(
    request: Request,
    current_user: User | None = Depends(get_current_user),
):
    """Render user registration page or redirect if already authenticated."""
    if current_user:
        return RedirectResponse(url="/watchlist", status_code=303)
    csrf_token = resolve_csrf_token(request)
    response = templates.TemplateResponse(
        request,
        "register.html",
        {"csrf_token": csrf_token, "error": None, "email": "", "is_auth_page": True},
    )
    set_csrf_cookie(response, csrf_token)
    return response


@router.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    """Register a standard user account with strong password (>=12 chars) and auto-login."""
    verify_csrf_request(request, csrf_token)

    normalized_email = email.strip().lower()
    fresh_csrf = resolve_csrf_token(request)

    def _error_response(message: str, status_code: int) -> HTMLResponse:
        resp = templates.TemplateResponse(
            request,
            "register.html",
            {
                "csrf_token": fresh_csrf,
                "error": message,
                "email": email,
                "is_auth_page": True,
            },
            status_code=status_code,
        )
        set_csrf_cookie(resp, fresh_csrf)
        return resp

    if "@" not in normalized_email or "." not in normalized_email.split("@", 1)[-1]:
        return _error_response("Introdu o adresă de email validă.", 400)

    if len(password) < 12:
        return _error_response("Parola trebuie să conțină cel puțin 12 caractere.", 400)

    try:
        password_hash = hash_password(password)
    except ValueError as exc:
        return _error_response(str(exc), 400)

    existing = db.scalar(select(User).where(User.email == normalized_email))
    if existing is not None:
        return _error_response("Există deja un cont înregistrat cu acest email.", 409)

    new_user = User(
        email=normalized_email,
        password_hash=password_hash,
        role="user",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_session_token(
        user_id=new_user.id,
        role=new_user.role,
        secret_key=settings.SECRET_KEY,
        expires_in_seconds=settings.SESSION_MAX_AGE_SECONDS,
    )
    response = RedirectResponse(url="/watchlist", status_code=303)
    set_session_cookie(response, token)
    return response


@router.post("/logout")
def logout(
    request: Request,
    csrf_token: str | None = Form(default=None),
) -> RedirectResponse:
    """Clear the signed session cookie and redirect to /login."""
    verify_csrf_request(request, csrf_token)
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=is_secure_cookie_env(),
    )
    return response


@router.get("/admin/status")
def admin_status(admin_user: User = Depends(require_admin)) -> dict[str, str]:
    """Role-protected endpoint verifying admin authorization."""
    return {
        "status": "ok",
        "admin_email": admin_user.email,
        "role": admin_user.role,
    }
