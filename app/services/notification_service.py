"""Email (SMTP) and Telegram Bot alert dispatchers with NotificationLog deduplication."""

from collections.abc import Callable
from email.message import EmailMessage
import smtplib

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.db.models import NotificationLog, ProductListing, User, WatchlistItem
from app.scraping.drift_detector import ScrapeOutcome
from app.services.watchlist_service import STORE_META

SmtpSender = Callable[[str, str, str], None]


def send_email_alert(
    *,
    to_email: str,
    subject: str,
    body: str,
    smtp_sender: SmtpSender | None = None,
) -> tuple[bool, str]:
    """Send an email alert via injected sender or configured SMTP server."""
    if smtp_sender is not None:
        try:
            smtp_sender(to_email, subject, body)
            return True, "Email trimis."
        except Exception as exc:
            return False, f"Eroare trimitere email: {exc}"

    if not settings.SMTP_HOST:
        return False, "SMTP neconfigurat (mod preview activ; preferințele sunt pregătite)."

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER or "noreply@pricemonitor.local"
    msg["To"] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as client:
            if settings.SMTP_PORT == 587:
                client.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                client.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            client.send_message(msg)
        return True, "Email trimis."
    except Exception as exc:
        return False, f"Eroare SMTP: {exc}"


def send_telegram_alert(
    *,
    chat_id: str | None,
    message: str,
    http_client: httpx.Client | None = None,
) -> tuple[bool, str]:
    """Send a Telegram Bot API message via injected httpx.Client or configured bot token."""
    if not chat_id or not chat_id.strip():
        return False, "Telegram Chat ID lipsă."
    if not settings.TELEGRAM_BOT_TOKEN:
        return False, "Telegram Bot Token neconfigurat (mod preview activ)."

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=10.0)
    try:
        resp = client.post(
            url,
            json={"chat_id": chat_id.strip(), "text": message},
        )
        if resp.status_code >= 400:
            return False, f"Eroare Telegram API ({resp.status_code})."
        return True, "Notificare Telegram trimisă."
    except httpx.HTTPError as exc:
        return False, f"Eroare rețea Telegram: {exc}"
    finally:
        if owns_client:
            client.close()


def _already_notified(
    db: Session,
    *,
    user_id: int,
    product_listing_id: int,
    channel: str,
    trigger_reason: str,
) -> bool:
    existing = db.scalar(
        select(NotificationLog.id).where(
            NotificationLog.user_id == user_id,
            NotificationLog.product_listing_id == product_listing_id,
            NotificationLog.channel == channel,
            NotificationLog.trigger_reason == trigger_reason,
        )
    )
    return existing is not None


def dispatch_price_drop_alerts(
    db: Session,
    *,
    listing: ProductListing,
    outcome: ScrapeOutcome,
    smtp_sender: SmtpSender | None = None,
    telegram_client: httpx.Client | None = None,
) -> int:
    """Dispatch deduplicated Email/Telegram alerts when a valid scrape hits target_price."""
    if (
        not outcome.should_notify_users
        or outcome.status != "valid"
        or listing.current_price is None
        or not listing.in_stock
    ):
        return 0

    rows = db.scalars(
        select(WatchlistItem)
        .where(
            WatchlistItem.canonical_product_id == listing.canonical_product_id,
            WatchlistItem.target_price.is_not(None),
            WatchlistItem.target_price >= listing.current_price,
        )
        .options(joinedload(WatchlistItem.user), joinedload(WatchlistItem.canonical_product))
    ).all()

    if not rows:
        return 0

    store_label = STORE_META.get(listing.store, {}).get("label", listing.store.upper())
    trigger_reason = f"target_price:{listing.current_price:.2f}"
    sent_count = 0

    for item in rows:
        user = item.user
        product = item.canonical_product
        subject = f"[PriceMonitor] Alertă preț {product.name} ({listing.current_price:.2f} RON)"
        payload = (
            f"{product.name} (SKU {product.sku}) a ajuns la {listing.current_price:.2f} RON "
            f"pe {store_label} (prag țintă: {item.target_price:.2f} RON). {listing.url}"
        )

        if user.email_enabled and item.notify_email:
            if not _already_notified(
                db,
                user_id=user.id,
                product_listing_id=listing.id,
                channel="email",
                trigger_reason=trigger_reason,
            ):
                ok, _ = send_email_alert(
                    to_email=user.email,
                    subject=subject,
                    body=payload,
                    smtp_sender=smtp_sender,
                )
                if ok:
                    db.add(
                        NotificationLog(
                            user_id=user.id,
                            product_listing_id=listing.id,
                            channel="email",
                            trigger_reason=trigger_reason,
                            message_payload=payload,
                        )
                    )
                    sent_count += 1

        if user.telegram_enabled and item.notify_telegram and user.telegram_chat_id:
            if not _already_notified(
                db,
                user_id=user.id,
                product_listing_id=listing.id,
                channel="telegram",
                trigger_reason=trigger_reason,
            ):
                ok, _ = send_telegram_alert(
                    chat_id=user.telegram_chat_id,
                    message=payload,
                    http_client=telegram_client,
                )
                if ok:
                    db.add(
                        NotificationLog(
                            user_id=user.id,
                            product_listing_id=listing.id,
                            channel="telegram",
                            trigger_reason=trigger_reason,
                            message_payload=payload,
                        )
                    )
                    sent_count += 1

    db.flush()
    return sent_count


def send_test_notification(
    db: Session,
    *,
    user: User,
    smtp_sender: SmtpSender | None = None,
    telegram_client: httpx.Client | None = None,
) -> list[str]:
    """Send a safe test alert for enabled channels or report preview mode status."""
    messages: list[str] = []
    if not user.email_enabled and not user.telegram_enabled:
        return ["Niciun canal activat. Activează Email sau Telegram pentru testare."]

    test_payload = (
        f"Notificare test P23 PriceMonitor pentru {user.email}. "
        "Preferințele tale de alertare sunt active."
    )
    if user.email_enabled:
        ok, status_msg = send_email_alert(
            to_email=user.email,
            subject="[PriceMonitor] Notificare test",
            body=test_payload,
            smtp_sender=smtp_sender,
        )
        messages.append(f"Email: {status_msg}")
        if ok:
            db.add(
                NotificationLog(
                    user_id=user.id,
                    product_listing_id=None,
                    channel="email",
                    trigger_reason="manual_test",
                    message_payload=test_payload,
                )
            )

    if user.telegram_enabled:
        ok, status_msg = send_telegram_alert(
            chat_id=user.telegram_chat_id,
            message=test_payload,
            http_client=telegram_client,
        )
        messages.append(f"Telegram: {status_msg}")
        if ok:
            db.add(
                NotificationLog(
                    user_id=user.id,
                    product_listing_id=None,
                    channel="telegram",
                    trigger_reason="manual_test",
                    message_payload=test_payload,
                )
            )

    db.commit()
    return messages


def get_user_notification_logs(
    db: Session,
    *,
    user_id: int,
    limit: int = 20,
) -> list[NotificationLog]:
    """Return most recent NotificationLog rows for a user."""
    return list(
        db.scalars(
            select(NotificationLog)
            .where(NotificationLog.user_id == user_id)
            .order_by(NotificationLog.sent_at.desc(), NotificationLog.id.desc())
            .limit(limit)
        ).all()
    )
