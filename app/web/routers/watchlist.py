from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_csrf_token
from app.db.models import User
from app.db.session import get_db
from app.services.watchlist_service import get_watchlist_dashboard_data
from app.web.deps import CSRF_COOKIE_NAME, is_secure_cookie_env, require_user, templates

router = APIRouter(tags=["watchlist"])


@router.get("/", response_class=HTMLResponse)
@router.get("/watchlist", response_class=HTMLResponse)
def watchlist_dashboard(
    request: Request,
    q: str = "",
    store: str = "all",
    sort: str = "lowest_price",
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Render DS-02 Live Watchlist connected to the database."""
    dashboard = get_watchlist_dashboard_data(
        db=db,
        user_id=current_user.id,
        q=q,
        store=store,
        sort=sort,
    )
    csrf_token = request.cookies.get(CSRF_COOKIE_NAME) or create_csrf_token(settings.SECRET_KEY)
    response = templates.TemplateResponse(
        request,
        "watchlist.html",
        {
            "user": current_user,
            "csrf_token": csrf_token,
            **dashboard,
        },
    )
    if CSRF_COOKIE_NAME not in request.cookies:
        response.set_cookie(
            key=CSRF_COOKIE_NAME,
            value=csrf_token,
            max_age=settings.SESSION_MAX_AGE_SECONDS,
            httponly=False,
            samesite="lax",
            secure=is_secure_cookie_env(),
            path="/",
        )
    return response
