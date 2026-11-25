from decimal import Decimal
from pathlib import Path

import httpx

from app.core.config import settings
from app.db.models import CanonicalProduct, ProductListing, User, WatchlistItem
from app.scraping.polite_client import PoliteHttpClient
from app.web.deps import get_polite_client

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _login_demo_user(test_client) -> None:
    resp = test_client.post(
        "/login",
        data={
            "email": settings.SEED_USER_EMAIL,
            "password": settings.SEED_USER_PASSWORD,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303


def _make_mock_polite_client(html_by_path: dict[str, str]) -> PoliteHttpClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        body = html_by_path.get(request.url.path)
        if body is None:
            return httpx.Response(404, text="Not Found")
        return httpx.Response(200, text=body)

    clock_val = [1000.0]

    def fake_clock() -> float:
        return clock_val[0]

    def fake_sleep(seconds: float) -> None:
        clock_val[0] += seconds

    return PoliteHttpClient(
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        clock=fake_clock,
        sleep_fn=fake_sleep,
    )


def test_post_watchlist_ingests_new_supported_url_offline_and_deduplicates(client) -> None:
    test_client, SessionLocal = client
    from app.main import app as fastapi_app

    # Build a new valid JD Sports product page (different sneaker not in seed)
    new_html = """<!DOCTYPE html>
    <html lang="ro"><body>
      <main class="product-view">
        <span class="product-brand">Nike</span>
        <h1 class="product-title">Nike Dunk Low Retro White Black Panda</h1>
        <span class="sku-value">DD1391-100</span>
        <div class="price-box">
          <span class="old-price"><del>649,99 lei</del></span>
          <span class="current-price">549,99 lei</span>
        </div>
        <div class="stock-status">În stoc</div>
        <img class="product-main-image" src="https://www.jdsports.ro/media/panda.jpg" />
      </main>
    </body></html>"""
    new_path = "/nike-dunk-low-retro-panda-dd1391-100"
    mock_polite = _make_mock_polite_client({new_path: new_html})
    test_client.app.dependency_overrides[get_polite_client] = lambda: mock_polite

    try:
        _login_demo_user(test_client)
        post_resp = test_client.post(
            "/watchlist",
            data={
                "url": f"https://www.jdsports.ro{new_path}",
                "target_price": "499.00",
            },
            follow_redirects=False,
        )
        assert post_resp.status_code == 303
        assert post_resp.headers["location"] == "/watchlist"

        with SessionLocal() as session:
            user = session.query(User).filter_by(email=settings.SEED_USER_EMAIL).one()
            prod = session.query(CanonicalProduct).filter_by(sku="DD1391-100").one()
            listing = session.query(ProductListing).filter_by(
                canonical_product_id=prod.id, store="jdsports"
            ).one()
            wl = session.query(WatchlistItem).filter_by(
                user_id=user.id, canonical_product_id=prod.id
            ).one()
            assert listing.current_price == Decimal("549.99")
            assert wl.target_price == Decimal("499.00")

        wl_page = test_client.get("/watchlist")
        assert wl_page.status_code == 200
        assert "DD1391-100" in wl_page.text
    finally:
        test_client.app.dependency_overrides.pop(get_polite_client, None)
        _ = fastapi_app


def test_post_watchlist_rejects_unsupported_domain_and_drift_html(client) -> None:
    test_client, SessionLocal = client

    broken_html = "<html><body><h1>404 Page</h1></body></html>"
    broken_path = "/broken-shoe-page"
    mock_polite = _make_mock_polite_client({broken_path: broken_html})
    test_client.app.dependency_overrides[get_polite_client] = lambda: mock_polite

    try:
        _login_demo_user(test_client)

        bad_domain = test_client.post(
            "/watchlist",
            data={"url": "https://www.zara.com/ro/en/sneakers-p123.html"},
            follow_redirects=False,
        )
        assert bad_domain.status_code == 400
        assert "nesuportat" in bad_domain.text.lower()

        drift_resp = test_client.post(
            "/watchlist",
            data={"url": f"https://www.jdsports.ro{broken_path}"},
            follow_redirects=False,
        )
        assert drift_resp.status_code == 400
        with SessionLocal() as session:
            assert (
                session.query(ProductListing)
                .filter_by(url=f"https://www.jdsports.ro{broken_path}")
                .one_or_none()
                is None
            )
    finally:
        test_client.app.dependency_overrides.pop(get_polite_client, None)


def test_authenticated_user_can_update_target_and_delete_watchlist_item_with_csrf(client) -> None:
    test_client, SessionLocal = client
    _login_demo_user(test_client)

    with SessionLocal() as session:
        prod = session.query(CanonicalProduct).filter_by(sku="553558-403").one()
        prod_id = prod.id

    # CSRF blocks cross-site POST
    csrf_block = test_client.post(
        f"/watchlist/{prod_id}/target",
        data={"target_price": "410.00"},
        headers={"Sec-Fetch-Site": "cross-site"},
        follow_redirects=False,
    )
    assert csrf_block.status_code == 403

    # Update target price
    upd_resp = test_client.post(
        f"/watchlist/{prod_id}/target",
        data={"target_price": "415.50"},
        follow_redirects=False,
    )
    assert upd_resp.status_code == 303
    assert upd_resp.headers["location"] == f"/products/{prod_id}"

    with SessionLocal() as session:
        user = session.query(User).filter_by(email=settings.SEED_USER_EMAIL).one()
        wl = session.query(WatchlistItem).filter_by(
            user_id=user.id, canonical_product_id=prod_id
        ).one()
        assert wl.target_price == Decimal("415.50")

    # Delete from watchlist
    del_resp = test_client.post(f"/watchlist/{prod_id}/delete", follow_redirects=False)
    assert del_resp.status_code == 303
    assert del_resp.headers["location"] == "/watchlist"

    with SessionLocal() as session:
        user = session.query(User).filter_by(email=settings.SEED_USER_EMAIL).one()
        assert (
            session.query(WatchlistItem)
            .filter_by(user_id=user.id, canonical_product_id=prod_id)
            .one_or_none()
            is None
        )
