from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db
from app.services.watchlist_service import get_watchlist_dashboard_data
from app.web.deps import require_user, templates

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
    return templates.TemplateResponse(
        request,
        "watchlist.html",
        {
            "user": current_user,
            **dashboard,
        },
    )
