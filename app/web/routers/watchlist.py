from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db
from app.scraping.polite_client import PoliteHttpClient
from app.services.ingestion_service import WatchlistIngestionError, ingest_product_url
from app.services.watchlist_service import (
    get_watchlist_dashboard_data,
    remove_watchlist_item,
    set_watchlist_target,
)
from app.web.deps import (
    ensure_csrf_cookie,
    get_polite_client,
    require_user,
    resolve_csrf_token,
    templates,
    verify_csrf_request,
)

router = APIRouter(tags=["watchlist"])


def _parse_optional_target_price(raw_target: str | None) -> Decimal | None:
    if raw_target is None or not raw_target.strip():
        return None
    normalized = raw_target.strip().replace(",", ".")
    try:
        val = Decimal(normalized).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise WatchlistIngestionError("Prețul țintă trebuie să fie un număr valid în RON.") from exc
    if val <= Decimal("0.00"):
        raise WatchlistIngestionError("Prețul țintă trebuie să fie mai mare de 0 RON.")
    return val


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
    csrf_token = resolve_csrf_token(request)
    response = templates.TemplateResponse(
        request,
        "watchlist.html",
        {
            "user": current_user,
            "csrf_token": csrf_token,
            "ingest_error": None,
            "submitted_url": "",
            "submitted_target": "",
            **dashboard,
        },
    )
    ensure_csrf_cookie(request, response, csrf_token)
    return response


@router.post("/watchlist", response_class=HTMLResponse)
def watchlist_ingest_url(
    request: Request,
    url: str = Form(...),
    target_price: str | None = Form(default=None),
    csrf_token: str | None = Form(default=None),
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
    polite_client: PoliteHttpClient = Depends(get_polite_client),
):
    """Ingest a supported store product URL into the user's watchlist."""
    verify_csrf_request(request, csrf_token)

    try:
        parsed_target = _parse_optional_target_price(target_price)
        ingest_product_url(
            db,
            user_id=current_user.id,
            url=url,
            target_price=parsed_target,
            polite_client=polite_client,
        )
    except WatchlistIngestionError as exc:
        dashboard = get_watchlist_dashboard_data(db=db, user_id=current_user.id)
        fresh_csrf = resolve_csrf_token(request)
        response = templates.TemplateResponse(
            request,
            "watchlist.html",
            {
                "user": current_user,
                "csrf_token": fresh_csrf,
                "ingest_error": str(exc),
                "submitted_url": url,
                "submitted_target": target_price or "",
                **dashboard,
            },
            status_code=400,
        )
        ensure_csrf_cookie(request, response, fresh_csrf)
        return response

    return RedirectResponse(url="/watchlist", status_code=303)


@router.post("/watchlist/{canonical_id}/target")
def watchlist_update_target(
    request: Request,
    canonical_id: int,
    target_price: str | None = Form(default=None),
    csrf_token: str | None = Form(default=None),
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Add or update the authenticated user's target price on a CanonicalProduct."""
    verify_csrf_request(request, csrf_token)
    try:
        parsed_target = _parse_optional_target_price(target_price)
    except WatchlistIngestionError:
        return RedirectResponse(url=f"/products/{canonical_id}", status_code=303)

    set_watchlist_target(
        db,
        user_id=current_user.id,
        canonical_product_id=canonical_id,
        target_price=parsed_target,
    )
    return RedirectResponse(url=f"/products/{canonical_id}", status_code=303)


@router.post("/watchlist/{canonical_id}/delete")
def watchlist_delete_item(
    request: Request,
    canonical_id: int,
    csrf_token: str | None = Form(default=None),
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Remove a CanonicalProduct from the authenticated user's watchlist."""
    verify_csrf_request(request, csrf_token)
    remove_watchlist_item(
        db,
        user_id=current_user.id,
        canonical_product_id=canonical_id,
    )
    return RedirectResponse(url="/watchlist", status_code=303)
