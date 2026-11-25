from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db
from app.services.watchlist_service import (
    get_product_detail_data,
    get_public_catalog_data,
)
from app.web.deps import (
    ensure_csrf_cookie,
    get_current_user,
    resolve_csrf_token,
    templates,
)

router = APIRouter(tags=["catalog"])


@router.get("/catalog", response_class=HTMLResponse)
def public_catalog(
    request: Request,
    q: str = "",
    store: str = "all",
    sort: str = "lowest_price",
    current_user: User | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Render public read-only canonical sneaker catalog for Guests and authenticated users."""
    data = get_public_catalog_data(
        db,
        q=q,
        store=store,
        sort=sort,
        user_id=current_user.id if current_user else None,
    )
    csrf_token = resolve_csrf_token(request)
    response = templates.TemplateResponse(
        request,
        "catalog.html",
        {
            "user": current_user,
            "csrf_token": csrf_token,
            **data,
        },
    )
    ensure_csrf_cookie(request, response, csrf_token)
    return response


@router.get("/products/{canonical_id}", response_class=HTMLResponse)
def product_detail(
    request: Request,
    canonical_id: int,
    current_user: User | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Render DS-03 cross-site product comparison and suspect-free price history."""
    detail = get_product_detail_data(
        db,
        canonical_id=canonical_id,
        user_id=current_user.id if current_user else None,
    )
    if detail is None:
        raise HTTPException(status_code=404, detail="Produsul solicitat nu a fost găsit.")

    csrf_token = resolve_csrf_token(request)
    response = templates.TemplateResponse(
        request,
        "product_detail.html",
        {
            "user": current_user,
            "csrf_token": csrf_token,
            **detail,
        },
    )
    ensure_csrf_cookie(request, response, csrf_token)
    return response
