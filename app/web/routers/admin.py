from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db
from app.services.admin_service import (
    confirm_deduplication_match,
    get_admin_dashboard_data,
    read_safe_snapshot,
    reject_deduplication_match,
    reset_store_adapter,
)
from app.web.deps import (
    ensure_csrf_cookie,
    require_admin_ssr,
    resolve_csrf_token,
    templates,
    verify_csrf_request,
)

router = APIRouter(tags=["admin"])


@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    snapshot_id: int | None = None,
    msg: str | None = None,
    admin_user: User = Depends(require_admin_ssr),
    db: Session = Depends(get_db),
):
    """Render DS-05 Admin Adapter Health, Snapshot Viewer, and SKU Deduplication Dashboard."""
    data = get_admin_dashboard_data(db, snapshot_id=snapshot_id)
    csrf_token = resolve_csrf_token(request)
    response = templates.TemplateResponse(
        request,
        "admin.html",
        {
            "user": admin_user,
            "csrf_token": csrf_token,
            "flash_message": msg,
            **data,
        },
    )
    ensure_csrf_cookie(request, response, csrf_token)
    return response


@router.get("/admin/snapshots/{log_id}", response_class=PlainTextResponse)
def admin_snapshot_raw(
    log_id: int,
    _admin_user: User = Depends(require_admin_ssr),
    db: Session = Depends(get_db),
):
    """Return raw HTML snapshot safely as text/plain from SNAPSHOTS_DIR."""
    loaded = read_safe_snapshot(db, log_id)
    if loaded is None:
        raise HTTPException(status_code=404, detail="Snapshot inexistent.")
    _, content = loaded
    return PlainTextResponse(content=content, media_type="text/plain; charset=utf-8")


@router.post("/admin/adapters/{store}/reset")
def admin_reset_adapter(
    request: Request,
    store: str,
    csrf_token: str | None = Form(default=None),
    _admin_user: User = Depends(require_admin_ssr),
    db: Session = Depends(get_db),
):
    """Reset a suspect or circuit-open store adapter back to healthy."""
    verify_csrf_request(request, csrf_token)
    if not reset_store_adapter(db, store):
        raise HTTPException(status_code=404, detail="Magazin necunoscut.")
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/admin/deduplication/{listing_id}/confirm")
def admin_confirm_dedup(
    request: Request,
    listing_id: int,
    csrf_token: str | None = Form(default=None),
    _admin_user: User = Depends(require_admin_ssr),
    db: Session = Depends(get_db),
):
    """Confirm and merge an uncertain ProductListing match onto its suggested CanonicalProduct."""
    verify_csrf_request(request, csrf_token)
    confirm_deduplication_match(db, listing_id)
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/admin/deduplication/{listing_id}/reject")
def admin_reject_dedup(
    request: Request,
    listing_id: int,
    csrf_token: str | None = Form(default=None),
    _admin_user: User = Depends(require_admin_ssr),
    db: Session = Depends(get_db),
):
    """Reject a suggested SKU merge so the listing remains a separate CanonicalProduct."""
    verify_csrf_request(request, csrf_token)
    reject_deduplication_match(db, listing_id)
    return RedirectResponse(url="/admin", status_code=303)
