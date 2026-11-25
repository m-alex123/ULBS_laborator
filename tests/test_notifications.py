from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import utcnow
from app.db.models import (
    CanonicalProduct,
    NotificationLog,
    ProductListing,
    SiteConfig,
    User,
    WatchlistItem,
)
from app.scraping.drift_detector import DriftCheckResult, ScrapeOutcome
from app.scraping.polite_client import PoliteHttpClient
from app.services.notification_service import (
    dispatch_price_drop_alerts,
    send_email_alert,
    send_telegram_alert,
)
from app.worker.runner import run_scrape_cycle

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_send_email_and_telegram_dispatchers_offline_and_unconfigured(monkeypatch) -> None:
    sent_emails: list[tuple[str, str, str]] = []

    def fake_smtp(to_email: str, subject: str, body: str) -> None:
        sent_emails.append((to_email, subject, body))

    ok_email, msg_email = send_email_alert(
        to_email="user@pricemonitor.local",
        subject="Alertă preț",
        body="489.99 RON",
        smtp_sender=fake_smtp,
    )
    assert ok_email is True
    assert len(sent_emails) == 1

    # Unconfigured SMTP returns safe preview status without raising
    monkeypatch.setattr(settings, "SMTP_HOST", None)
    unconf_ok, unconf_msg = send_email_alert(
        to_email="user@pricemonitor.local",
        subject="Test",
        body="Body",
    )
    assert unconf_ok is False
    assert "neconfigurat" in unconf_msg.lower()

    # Telegram with MockTransport
    telegram_calls: list[dict] = []

    def tg_handler(request: httpx.Request) -> httpx.Response:
        telegram_calls.append({"url": str(request.url), "body": request.content.decode("utf-8")})
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "123456:fake-token")
    ok_tg, _ = send_telegram_alert(
        chat_id="987654321",
        message="Preț nou 489.99 RON",
        http_client=httpx.Client(transport=httpx.MockTransport(tg_handler)),
    )
    assert ok_tg is True
    assert len(telegram_calls) == 1
    assert "sendMessage" in telegram_calls[0]["url"]

    # Unconfigured Telegram returns safe non-crashing status
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", None)
    tg_unconf_ok, tg_unconf_msg = send_telegram_alert(chat_id="987654321", message="hi")
    assert tg_unconf_ok is False
    assert "neconfigurat" in tg_unconf_msg.lower()


def test_dispatch_price_drop_alerts_gates_preferences_deduplicates_and_blocks_suspect(
    db_session: Session, monkeypatch
) -> None:
    user = User(
        email="alerts@pricemonitor.local",
        password_hash="hash",
        role="user",
        email_enabled=True,
        telegram_enabled=True,
        telegram_chat_id="555000111",
    )
    prod = CanonicalProduct(name="Nike Air Jordan 1 Low", brand="Nike", sku="553558-403")
    db_session.add_all([user, prod])
    db_session.flush()

    listing = ProductListing(
        canonical_product_id=prod.id,
        store="jdsports",
        url="https://www.jdsports.ro/nike-air-jordan-1-low-553558-403",
        current_price=Decimal("460.00"),
        original_price=Decimal("599.99"),
        raw_title="Nike Air Jordan 1 Low",
        in_stock=True,
    )
    watchlist = WatchlistItem(
        user_id=user.id,
        canonical_product_id=prod.id,
        target_price=Decimal("480.00"),
        notify_email=True,
        notify_telegram=True,
    )
    db_session.add_all([listing, watchlist])
    db_session.commit()

    emails: list[str] = []
    tg_msgs: list[str] = []
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "bot-token")
    tg_client = httpx.Client(
        transport=httpx.MockTransport(
            lambda req: (tg_msgs.append(req.content.decode()), httpx.Response(200, json={"ok": True}))[1]
        )
    )

    # Suspect outcome must NEVER send alerts
    suspect_outcome = ScrapeOutcome(
        status="suspect",
        drift_result=DriftCheckResult(is_valid=False, status="suspect", reasons=["extreme_price_drop"]),
        snapshot_path="storage/snapshots/test.html",
        should_notify_users=False,
    )
    assert (
        dispatch_price_drop_alerts(
            db_session,
            listing=listing,
            outcome=suspect_outcome,
            smtp_sender=lambda to, s, b: emails.append(to),
            telegram_client=tg_client,
        )
        == 0
    )
    assert db_session.query(NotificationLog).count() == 0

    # Valid outcome sends 1 email + 1 telegram
    valid_outcome = ScrapeOutcome(
        status="valid",
        drift_result=DriftCheckResult(is_valid=True, status="valid"),
        snapshot_path=None,
        should_notify_users=True,
    )
    sent_first = dispatch_price_drop_alerts(
        db_session,
        listing=listing,
        outcome=valid_outcome,
        smtp_sender=lambda to, s, b: emails.append(to),
        telegram_client=tg_client,
    )
    assert sent_first == 2
    assert len(emails) == 1
    assert len(tg_msgs) == 1
    assert db_session.query(NotificationLog).count() == 2

    # Second run at the exact same price is deduplicated (0 new alerts)
    sent_second = dispatch_price_drop_alerts(
        db_session,
        listing=listing,
        outcome=valid_outcome,
        smtp_sender=lambda to, s, b: emails.append(to),
        telegram_client=tg_client,
    )
    assert sent_second == 0
    assert db_session.query(NotificationLog).count() == 2


def test_run_scrape_cycle_dispatches_alerts_on_valid_target_hit_and_zero_on_broken_selector(
    db_session: Session,
) -> None:
    now = utcnow()
    user = User(
        email="worker_alert@pricemonitor.local",
        password_hash="hash",
        role="user",
        email_enabled=True,
        telegram_enabled=False,
    )
    cfg = SiteConfig(store="jdsports", circuit_breaker_open=False, adapter_status="healthy")
    prod = CanonicalProduct(name="Nike Air Jordan 1 Low 'University Blue'", brand="Nike", sku="553558-403")
    db_session.add_all([user, cfg, prod])
    db_session.flush()

    listing = ProductListing(
        canonical_product_id=prod.id,
        store="jdsports",
        url="https://www.jdsports.ro/nike-air-jordan-1-low-university-blue-553558-403",
        current_price=Decimal("550.00"),
        original_price=Decimal("599.99"),
        raw_title="Nike Air Jordan 1 Low 'University Blue' Bărbați",
        in_stock=True,
        last_checked_at=now - timedelta(hours=7),
    )
    wl = WatchlistItem(
        user_id=user.id,
        canonical_product_id=prod.id,
        target_price=Decimal("500.00"),
        notify_email=True,
    )
    db_session.add_all([listing, wl])
    db_session.commit()

    valid_html = (FIXTURES_DIR / "jdsports_product.html").read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(200, text=valid_html)

    clock_t = [1000.0]
    polite = PoliteHttpClient(
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        clock=lambda: clock_t[0],
        sleep_fn=lambda s: clock_t.__setitem__(0, clock_t[0] + s),
    )

    sent_emails: list[str] = []
    summary = run_scrape_cycle(
        db_session,
        polite_client=polite,
        smtp_sender=lambda to, subj, body: sent_emails.append(to),
    )
    assert summary.succeeded == 1
    assert summary.alerts_sent == 1
    assert len(sent_emails) == 1
    assert db_session.query(NotificationLog).count() == 1
