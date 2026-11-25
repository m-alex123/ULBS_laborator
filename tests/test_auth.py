import time

from app.core.config import settings
from app.core.security import create_session_token, decode_session_token


def test_session_token_roundtrip_and_tamper_rejection() -> None:
    token = create_session_token(user_id=7, role="user", secret_key="unit-secret")
    decoded = decode_session_token(token, secret_key="unit-secret")

    assert decoded is not None
    assert decoded["user_id"] == 7
    assert decoded["role"] == "user"

    assert decode_session_token(token, secret_key="wrong-secret") is None
    assert decode_session_token(f"{token}tampered", secret_key="unit-secret") is None
    assert decode_session_token("invalid-format", secret_key="unit-secret") is None


def test_session_token_rejects_expired_token() -> None:
    token = create_session_token(
        user_id=3,
        role="admin",
        secret_key="unit-secret",
        expires_in_seconds=-10,
    )
    assert decode_session_token(token, secret_key="unit-secret") is None
    assert int(time.time()) > 0


def test_login_page_renders_ds01_shell(client) -> None:
    test_client, _ = client
    response = test_client.get("/login")

    assert response.status_code == 200
    assert "PriceMonitor" in response.text
    assert 'name="email"' in response.text
    assert 'name="password"' in response.text


def test_login_success_sets_httponly_cookie_and_redirects(client) -> None:
    test_client, _ = client
    response = test_client.post(
        "/login",
        data={
            "email": settings.SEED_USER_EMAIL,
            "password": settings.SEED_USER_PASSWORD,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/watchlist"
    set_cookie = response.headers.get("set-cookie", "")
    assert settings.SESSION_COOKIE_NAME in set_cookie
    assert "HttpOnly" in set_cookie or "httponly" in set_cookie.lower()


def test_login_invalid_credentials_returns_401(client) -> None:
    test_client, _ = client
    response = test_client.post(
        "/login",
        data={
            "email": settings.SEED_USER_EMAIL,
            "password": "WrongPassword999!",
        },
        follow_redirects=False,
    )

    assert response.status_code == 401
    assert "Email sau parolă incorectă" in response.text


def test_logout_clears_cookie_and_redirects_to_login(client) -> None:
    test_client, _ = client
    test_client.post(
        "/login",
        data={
            "email": settings.SEED_USER_EMAIL,
            "password": settings.SEED_USER_PASSWORD,
        },
        follow_redirects=False,
    )

    logout_resp = test_client.post("/logout", follow_redirects=False)
    assert logout_resp.status_code == 303
    assert logout_resp.headers["location"] == "/login"

    watchlist_resp = test_client.get("/watchlist", follow_redirects=False)
    assert watchlist_resp.status_code == 303
    assert watchlist_resp.headers["location"] == "/login"


def test_admin_role_enforcement(client) -> None:
    test_client, _ = client

    # Unauthenticated -> 401
    anon_resp = test_client.get("/admin/status", follow_redirects=False)
    assert anon_resp.status_code == 401

    # Regular user -> 403
    test_client.post(
        "/login",
        data={
            "email": settings.SEED_USER_EMAIL,
            "password": settings.SEED_USER_PASSWORD,
        },
        follow_redirects=False,
    )
    user_resp = test_client.get("/admin/status")
    assert user_resp.status_code == 403

    # Admin user -> 200
    test_client.post(
        "/login",
        data={
            "email": settings.SEED_ADMIN_EMAIL,
            "password": settings.SEED_ADMIN_PASSWORD,
        },
        follow_redirects=False,
    )
    admin_resp = test_client.get("/admin/status")
    assert admin_resp.status_code == 200
    assert admin_resp.json()["role"] == "admin"
    assert admin_resp.json()["admin_email"] == settings.SEED_ADMIN_EMAIL
