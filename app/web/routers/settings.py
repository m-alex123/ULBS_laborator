from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.db.models import User, WatchlistItem
from app.db.session import get_db
from app.services.notification_service import (
    get_user_notification_logs,
    send_test_notification,
)
from app.web.deps import (
    ensure_csrf_cookie,
    require_user,
    resolve_csrf_token,
    templates,
    verify_csrf_request,
)

router = APIRouter(tags=["settings"])


@router.get("/settings", response_class=HTMLResponse)
def settings_page(
    request: Request,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Render DS-04 Notification & Profile Settings page."""
    csrf_token = resolve_csrf_token(request)
    logs = get_user_notification_logs(db, user_id=current_user.id)
    response = templates.TemplateResponse(
        request,
        "settings.html",
        {
            "user": current_user,
            "csrf_token": csrf_token,
            "logs": logs,
            "status_messages": [],
            "error": None,
        },
    )
    ensure_csrf_cookie(request, response, csrf_token)
    return response


@router.post("/settings/notifications", response_class=HTMLResponse)
def update_notification_settings(
    request: Request,
    action: str = Form(default="save"),
    email_enabled: str | None = Form(default=None),
    telegram_enabled: str | None = Form(default=None),
    telegram_chat_id: str | None = Form(default=None),
    csrf_token: str | None = Form(default=None),
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Save User Email/Telegram notification preferences or trigger a safe test notification."""
    verify_csrf_request(request, csrf_token)

    email_flag = email_enabled is not None
    telegram_flag = telegram_enabled is not None
    cleaned_chat_id = telegram_chat_id.strip() if telegram_chat_id and telegram_chat_id.strip() else None

    error: str | None = None
    status_messages: list[str] = []

    if telegram_flag and not cleaned_chat_id:
        error = "Introdu un Telegram Chat ID valid înainte de a activa alertele Telegram."
    else:
        current_user.email_enabled = email_flag
        current_user.telegram_enabled = telegram_flag
        current_user.telegram_chat_id = cleaned_chat_id
        db.execute(
            update(WatchlistItem)
            .where(WatchlistItem.user_id == current_user.id)
            .values(notify_email=email_flag, notify_telegram=telegram_flag)
        )
        db.commit()
        db.refresh(current_user)
        status_messages.append("Preferințele de notificare au fost salvate.")

        if action.strip().lower() == "test":
            test_msgs = send_test_notification(db, user=current_user)
            status_messages.extend(test_msgs)

    fresh_csrf = resolve_csrf_token(request)
    logs = get_user_notification_logs(db, user_id=current_user.id)
    response = templates.TemplateResponse(
        request,
        "settings.html",
        {
            "user": current_user,
            "csrf_token": fresh_csrf,
            "logs": logs,
            "status_messages": status_messages,
            "error": error,
        },
        status_code=400 if error else 200,
    )
    ensure_csrf_cookie(request, response, fresh_csrf)
    return response
