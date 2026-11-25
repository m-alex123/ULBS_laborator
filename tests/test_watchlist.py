from decimal import Decimal

from app.core.config import settings
from app.db.models import CanonicalProduct, ProductListing, SiteConfig, User, WatchlistItem


def _login_as_demo_user(test_client) -> None:
    resp = test_client.post(
        "/login",
        data={
            "email": settings.SEED_USER_EMAIL,
            "password": settings.SEED_USER_PASSWORD,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_watchlist_redirects_unauthenticated_users(client) -> None:
    test_client, _ = client

    for path in ("/", "/watchlist"):
        resp = test_client.get(path, follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login"


def test_watchlist_renders_seeded_sneakers_with_real_photos_and_badges(client) -> None:
    test_client, _ = client
    _login_as_demo_user(test_client)

    resp = test_client.get("/watchlist")
    assert resp.status_code == 200

    html = resp.text
    assert "553558-403" in html
    assert "HQ8708" in html
    assert "DZ5485-612" in html
    assert "images.stockx.com" in html
    assert "handleSneakerImgError" in html
    assert "photo-retailer-badge" in html
    assert "489.99 RON" in html
    assert "449.90 RON" in html
    assert "899.99 RON" in html

    root_resp = test_client.get("/")
    assert root_resp.status_code == 200
    assert "Live Watchlist" in root_resp.text


def test_watchlist_search_store_filter_and_sort(client) -> None:
    test_client, SessionLocal = client
    _login_as_demo_user(test_client)

    # Search filter by SKU
    search_resp = test_client.get("/watchlist", params={"q": "HQ8708"})
    assert search_resp.status_code == 200
    assert "HQ8708" in search_resp.text
    assert "553558-403" not in search_resp.text

    # Add a product listed ONLY on sizeer to verify store filter excludes non-matching stores
    with SessionLocal() as session:
        user = session.query(User).filter_by(email=settings.SEED_USER_EMAIL).one()
        only_sizeer = CanonicalProduct(
            name="Puma Palermo Sizeer Exclusive",
            brand="Puma",
            sku="396463-99",
            image_url="https://images.stockx.com/images/adidas-Campus-00s-Core-Black-Product.jpg",
        )
        session.add(only_sizeer)
        session.flush()
        session.add(
            ProductListing(
                canonical_product_id=only_sizeer.id,
                store="sizeer",
                url="https://sizeer.ro/puma-palermo-396463-99",
                current_price=Decimal("399.99"),
                original_price=Decimal("499.99"),
                raw_title="Puma Palermo Sizeer Exclusive",
                in_stock=True,
            )
        )
        session.add(WatchlistItem(user_id=user.id, canonical_product_id=only_sizeer.id))
        session.commit()

    jd_resp = test_client.get("/watchlist", params={"store": "jdsports"})
    assert jd_resp.status_code == 200
    assert "396463-99" not in jd_resp.text
    assert "553558-403" in jd_resp.text

    sizeer_resp = test_client.get("/watchlist", params={"store": "sizeer"})
    assert sizeer_resp.status_code == 200
    assert "396463-99" in sizeer_resp.text

    sort_resp = test_client.get("/watchlist", params={"sort": "biggest_discount"})
    assert sort_resp.status_code == 200
    assert "396463-99" in sort_resp.text


def test_watchlist_shows_circuit_breaker_banner_and_empty_state(client) -> None:
    test_client, SessionLocal = client

    with SessionLocal() as session:
        buzz = session.query(SiteConfig).filter_by(store="buzzsneakers").one()
        buzz.circuit_breaker_open = True
        session.commit()

    # Admin user has 0 watchlist items -> tests both empty state and CB banner
    admin_login = test_client.post(
        "/login",
        data={
            "email": settings.SEED_ADMIN_EMAIL,
            "password": settings.SEED_ADMIN_PASSWORD,
        },
        follow_redirects=False,
    )
    assert admin_login.status_code == 303

    resp = test_client.get("/watchlist")
    assert resp.status_code == 200
    assert "CIRCUIT BREAKER ACTIVAT" in resp.text
    assert "buzzsneakers.ro" in resp.text
    assert "Niciun sneaker în monitorizare" in resp.text
