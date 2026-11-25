from app.core.config import settings
from app.db.models import NotificationLog, User


def _login_demo_user(test_client) -> None:
    resp = test_client.post(
        "/login",
        data={"email": settings.SEED_USER_EMAIL, "password": settings.SEED_USER_PASSWORD},
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_settings_redirects_guests_to_login(client) -> None:
    test_client, _ = client

    assert test_client.get("/settings", follow_redirects=False).status_code == 303
    assert test_client.get("/settings", follow_redirects=False).headers["location"] == "/login"

    post_resp = test_client.post(
        "/settings/notifications",
        data={"email_enabled": "on"},
        follow_redirects=False,
    )
    assert post_resp.status_code == 303
    assert post_resp.headers["location"] == "/login"


def test_settings_updates_preferences_runs_safe_test_preview_and_lists_logs(
    client, monkeypatch
) -> None:
    test_client, SessionLocal = client
    monkeypatch.setattr(settings, "SMTP_HOST", None)
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", None)
    _login_demo_user(test_client)

    with SessionLocal() as session:
        user = session.query(User).filter_by(email=settings.SEED_USER_EMAIL).one()
        session.add(
            NotificationLog(
                user_id=user.id,
                product_listing_id=None,
                channel="email",
                trigger_reason="target_price:489.99",
                message_payload="Preț scăzut la 489.99 RON",
            )
        )
        session.commit()

    page = test_client.get("/settings")
    assert page.status_code == 200
    assert settings.SEED_USER_EMAIL in page.text
    assert "489.99 RON" in page.text
    csrf_tok = test_client.cookies.get("p23_csrf")

    # CSRF blocks cross-site submission
    cross = test_client.post(
        "/settings/notifications",
        data={"telegram_chat_id": "12345"},
        headers={"Sec-Fetch-Site": "cross-site"},
        follow_redirects=False,
    )
    assert cross.status_code == 403

    # Save preferences
    save_resp = test_client.post(
        "/settings/notifications",
        data={
            "action": "save",
            "email_enabled": "on",
            "telegram_enabled": "on",
            "telegram_chat_id": "77889900",
            "csrf_token": csrf_tok,
        },
        follow_redirects=False,
    )
    assert save_resp.status_code == 200
    assert "Preferințele de notificare au fost salvate" in save_resp.text

    with SessionLocal() as session:
        user = session.query(User).filter_by(email=settings.SEED_USER_EMAIL).one()
        assert user.email_enabled is True
        assert user.telegram_enabled is True
        assert user.telegram_chat_id == "77889900"

    # Trigger safe test notification in unconfigured environment -> preview notice, no 500
    test_resp = test_client.post(
        "/settings/notifications",
        data={
            "action": "test",
            "email_enabled": "on",
            "telegram_enabled": "on",
            "telegram_chat_id": "77889900",
            "csrf_token": csrf_tok,
        },
        follow_redirects=False,
    )
    assert test_resp.status_code == 200
    assert "preview" in test_resp.text.lower() or "neconfigurat" in test_resp.text.lower()
