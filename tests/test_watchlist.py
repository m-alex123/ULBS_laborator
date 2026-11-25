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


def test_watchlist_edge_cases_zero_price_out_of_stock_and_http_image_blocked(client) -> None:
    test_client, SessionLocal = client
    from app.services.watchlist_service import build_sparkline

    assert build_sparkline([]).points == "2,14 70,14"
    assert build_sparkline([Decimal("100.00"), Decimal("100.00")]).points == "2,14 70,14"

    _login_as_demo_user(test_client)

    with SessionLocal() as session:
        user = session.query(User).filter_by(email=settings.SEED_USER_EMAIL).one()
        edge_prod = CanonicalProduct(
            name="Edge Case Sneaker",
            brand="Nike",
            sku="EDGE-001",
            image_url="http://insecure.example/shoe.jpg",
        )
        session.add(edge_prod)
        session.flush()
        session.add(
            ProductListing(
                canonical_product_id=edge_prod.id,
                store="jdsports",
                url="https://www.jdsports.ro/edge-001",
                current_price=Decimal("0.00"),
                original_price=Decimal("500.00"),
                raw_title="Zero Price Out Of Stock",
                in_stock=False,
            )
        )
        session.add(WatchlistItem(user_id=user.id, canonical_product_id=edge_prod.id))
        session.commit()

    resp = test_client.get("/watchlist", params={"q": "EDGE-001", "sort": "biggest_discount"})
    assert resp.status_code == 200
    assert "EDGE-001" in resp.text
    assert "http://insecure.example/shoe.jpg" not in resp.text
    assert "MOD OFFLINE" in resp.text
    assert "OFERTĂ:" not in resp.text
    assert "-100%" not in resp.text

    no_match = test_client.get("/watchlist", params={"q": "NONEXISTENT-SKU-XYZ"})
    assert no_match.status_code == 200
    assert "Niciun rezultat pentru filtrele curente" in no_match.text
