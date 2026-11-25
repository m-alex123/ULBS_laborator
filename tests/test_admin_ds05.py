from decimal import Decimal

from app.core.config import settings
from app.db.models import (
    AdapterRunLog,
    CanonicalProduct,
    ProductListing,
    SiteConfig,
)


def _login_as(test_client, email: str, password: str) -> None:
    resp = test_client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_admin_dashboard_rbac_redirects_guest_forbids_user_and_preserves_c002_api(client) -> None:
    test_client, _ = client

    # Guest on SSR /admin -> 303 -> /login
    guest_admin = test_client.get("/admin", follow_redirects=False)
    assert guest_admin.status_code == 303
    assert guest_admin.headers["location"] == "/login"

    # Guest on /admin/status preserves C-002 (401)
    assert test_client.get("/admin/status", follow_redirects=False).status_code == 401

    # Regular user -> 403 on both /admin and mutating actions
    _login_as(test_client, settings.SEED_USER_EMAIL, settings.SEED_USER_PASSWORD)
    assert test_client.get("/admin", follow_redirects=False).status_code == 403
    assert test_client.post("/admin/adapters/jdsports/reset", follow_redirects=False).status_code == 403
    assert test_client.post("/admin/deduplication/1/confirm", follow_redirects=False).status_code == 403


def test_admin_views_health_escaped_snapshot_and_resets_suspect_adapter(client) -> None:
    test_client, SessionLocal = client

    snapshot_file = settings.SNAPSHOTS_DIR / "jdsports_suspect_demo.html"
    snapshot_file.parent.mkdir(parents=True, exist_ok=True)
    snapshot_file.write_text(
        "<html><body><h1>Broken</h1><script>alert('xss')</script></body></html>",
        encoding="utf-8",
    )

    with SessionLocal() as session:
        cfg = session.query(SiteConfig).filter_by(store="jdsports").one()
        cfg.adapter_status = "suspect"
        cfg.circuit_breaker_open = True
        log1 = AdapterRunLog(
            store="jdsports",
            status="failed",
            error_message="HTTP 503",
        )
        log2 = AdapterRunLog(
            store="jdsports",
            status="suspect",
            error_message="missing_price",
            snapshot_path=str(snapshot_file),
        )
        session.add_all([log1, log2])
        session.commit()
        suspect_log_id = log2.id

    _login_as(test_client, settings.SEED_ADMIN_EMAIL, settings.SEED_ADMIN_PASSWORD)

    dash = test_client.get("/admin", params={"snapshot_id": suspect_log_id})
    assert dash.status_code == 200
    assert "jdsports.ro" in dash.text
    assert "suspect" in dash.text.lower()
    assert "missing_price" in dash.text
    # Snapshot HTML must be escaped (no raw <script>alert('xss')</script> injected!)
    assert "<script>alert('xss')</script>" not in dash.text
    assert "&lt;script&gt;alert" in dash.text

    snap_resp = test_client.get(f"/admin/snapshots/{suspect_log_id}")
    assert snap_resp.status_code == 200
    assert "missing_price" not in snap_resp.text  # raw text/plain preview of file
    assert "Broken" in snap_resp.text

    csrf_tok = test_client.cookies.get("p23_csrf")
    reset_resp = test_client.post(
        "/admin/adapters/jdsports/reset",
        data={"csrf_token": csrf_tok},
        follow_redirects=False,
    )
    assert reset_resp.status_code == 303
    assert reset_resp.headers["location"] == "/admin"

    with SessionLocal() as session:
        cfg = session.query(SiteConfig).filter_by(store="jdsports").one()
        assert cfg.adapter_status == "healthy"
        assert cfg.circuit_breaker_open is False


def test_admin_can_confirm_and_reject_uncertain_sku_matches(client) -> None:
    test_client, SessionLocal = client

    with SessionLocal() as session:
        target = CanonicalProduct(name="Puma Palermo Leather", brand="Puma", sku="396463-01")
        provisional_confirm = CanonicalProduct(
            name="Puma Palermo",
            brand="Puma",
            sku="UNVERIFIED-SIZEER-AAA111",
        )
        provisional_reject = CanonicalProduct(
            name="Puma Suede Classic",
            brand="Puma",
            sku="UNVERIFIED-BUZZ-BBB222",
        )
        session.add_all([target, provisional_confirm, provisional_reject])
        session.flush()

        listing_confirm = ProductListing(
            canonical_product_id=provisional_confirm.id,
            store="sizeer",
            url="https://sizeer.ro/puma-palermo-unverified",
            current_price=Decimal("429.99"),
            raw_title="Puma Palermo",
            match_needs_review=True,
            match_confidence=0.74,
            suggested_canonical_product_id=target.id,
        )
        listing_reject = ProductListing(
            canonical_product_id=provisional_reject.id,
            store="buzzsneakers",
            url="https://www.buzzsneakers.ro/puma-suede-unverified",
            current_price=Decimal("399.99"),
            raw_title="Puma Suede Classic",
            match_needs_review=True,
            match_confidence=0.62,
            suggested_canonical_product_id=target.id,
        )
        session.add_all([listing_confirm, listing_reject])
        session.commit()
        confirm_id = listing_confirm.id
        reject_id = listing_reject.id
        target_id = target.id
        provisional_reject_id = provisional_reject.id

    _login_as(test_client, settings.SEED_ADMIN_EMAIL, settings.SEED_ADMIN_PASSWORD)
    dash = test_client.get("/admin")
    assert dash.status_code == 200
    assert "Puma Palermo" in dash.text
    csrf_tok = test_client.cookies.get("p23_csrf")

    conf_resp = test_client.post(
        f"/admin/deduplication/{confirm_id}/confirm",
        data={"csrf_token": csrf_tok},
        follow_redirects=False,
    )
    assert conf_resp.status_code == 303

    rej_resp = test_client.post(
        f"/admin/deduplication/{reject_id}/reject",
        data={"csrf_token": csrf_tok},
        follow_redirects=False,
    )
    assert rej_resp.status_code == 303

    with SessionLocal() as session:
        merged = session.get(ProductListing, confirm_id)
        rejected = session.get(ProductListing, reject_id)
        assert merged is not None
        assert merged.canonical_product_id == target_id
        assert merged.match_needs_review is False
        assert merged.suggested_canonical_product_id is None

        assert rejected is not None
        assert rejected.canonical_product_id == provisional_reject_id
        assert rejected.match_needs_review is False
        assert rejected.suggested_canonical_product_id is None
