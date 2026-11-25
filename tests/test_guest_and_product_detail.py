from datetime import timedelta
from decimal import Decimal

from app.core.config import settings
from app.db.base import utcnow
from app.db.models import CanonicalProduct, PriceHistory, ProductListing, User


def test_login_page_has_continue_as_guest_and_register_links(client) -> None:
    test_client, _ = client
    resp = test_client.get("/login")
    assert resp.status_code == 200
    assert "/catalog" in resp.text
    assert "Continuă ca Vizitator" in resp.text
    assert "/register" in resp.text


def test_guest_can_browse_public_catalog_and_ds03_read_only(client) -> None:
    test_client, _ = client

    catalog_resp = test_client.get("/catalog")
    assert catalog_resp.status_code == 200
    html = catalog_resp.text
    assert "MOD VIZITATOR" in html
    assert "Autentificare" in html
    assert "Înregistrare" in html
    assert "553558-403" in html
    assert "HQ8708" in html
    assert "DZ5485-612" in html
    assert "/products/1" in html

    detail_resp = test_client.get("/products/1")
    assert detail_resp.status_code == 200
    detail_html = detail_resp.text
    assert "MOD VIZITATOR" in detail_html
    assert "553558-403" in detail_html
    assert "JD SPORTS" in detail_html
    assert "SIZEER" in detail_html
    assert "BUZZ SNEAKERS" in detail_html
    assert "489.99 RON" in detail_html
    assert "price-history-chart" in detail_html
    # Guest sees login CTA instead of watchlist mutation form
    assert 'action="/watchlist/1/delete"' not in detail_html
    assert 'action="/watchlist/1/target"' not in detail_html


def test_ds03_excludes_suspect_and_error_history_from_stats_and_chart(client) -> None:
    test_client, SessionLocal = client

    with SessionLocal() as session:
        product = session.query(CanonicalProduct).filter_by(sku="553558-403").one()
        listing = session.query(ProductListing).filter_by(
            canonical_product_id=product.id, store="jdsports"
        ).one()
        # Inject a bogus 99% drop suspect row and an error row
        now = utcnow()
        session.add_all(
            [
                PriceHistory(
                    product_listing_id=listing.id,
                    price=Decimal("4.99"),
                    currency="RON",
                    in_stock=True,
                    recorded_at=now + timedelta(minutes=5),
                    status="suspect",
                ),
                PriceHistory(
                    product_listing_id=listing.id,
                    price=None,
                    currency="RON",
                    in_stock=False,
                    recorded_at=now + timedelta(minutes=10),
                    status="error",
                ),
            ]
        )
        session.commit()
        product_id = product.id

    resp = test_client.get(f"/products/{product_id}")
    assert resp.status_code == 200
    assert "4.99" not in resp.text
    assert "489.99 RON" in resp.text


def test_ds03_returns_404_for_missing_product(client) -> None:
    test_client, _ = client
    resp = test_client.get("/products/999999")
    assert resp.status_code == 404


def test_guest_cannot_access_mutating_or_admin_routes(client) -> None:
    test_client, _ = client

    # Existing C-003 watchlist routes redirect guests -> /login
    for path in ("/", "/watchlist"):
        resp = test_client.get(path, follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login"

    # Mutating watchlist endpoints redirect guests -> /login
    for path, data in (
        ("/watchlist", {"url": "https://www.jdsports.ro/test-shoe"}),
        ("/watchlist/1/target", {"target_price": "450.00"}),
        ("/watchlist/1/delete", {}),
    ):
        resp = test_client.post(path, data=data, follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login"

    # Admin route stays strictly 401 for guests
    admin_resp = test_client.get("/admin/status", follow_redirects=False)
    assert admin_resp.status_code == 401


def test_register_creates_user_with_strong_password_and_sets_session_cookie(client) -> None:
    test_client, SessionLocal = client

    get_reg = test_client.get("/register")
    assert get_reg.status_code == 200
    assert 'name="email"' in get_reg.text
    assert 'name="password"' in get_reg.text
    csrf_tok = test_client.cookies.get("p23_csrf")

    # Reject short password (<12 chars)
    weak_resp = test_client.post(
        "/register",
        data={"email": "newstudent@ulbs.ro", "password": "Short123!", "csrf_token": csrf_tok},
        follow_redirects=False,
    )
    assert weak_resp.status_code == 400
    assert "12 caractere" in weak_resp.text

    # Reject duplicate email
    dup_resp = test_client.post(
        "/register",
        data={
            "email": settings.SEED_USER_EMAIL,
            "password": "StrongPassword2026!",
            "csrf_token": csrf_tok,
        },
        follow_redirects=False,
    )
    assert dup_resp.status_code == 409

    # Valid registration creates role='user' and auto-logs into /watchlist
    ok_resp = test_client.post(
        "/register",
        data={
            "email": "NewStudent@ulbs.ro",
            "password": "StrongPassword2026!",
            "csrf_token": csrf_tok,
        },
        follow_redirects=False,
    )
    assert ok_resp.status_code == 303
    assert ok_resp.headers["location"] == "/watchlist"
    assert settings.SESSION_COOKIE_NAME in ok_resp.headers.get("set-cookie", "")

    with SessionLocal() as session:
        created = session.query(User).filter_by(email="newstudent@ulbs.ro").one()
        assert created.role == "user"

    wl_resp = test_client.get("/watchlist")
    assert wl_resp.status_code == 200
    assert "newstudent@ulbs.ro" in wl_resp.text
