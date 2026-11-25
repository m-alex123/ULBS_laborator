from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import utcnow
from app.db.models import (
    AdapterRunLog,
    CanonicalProduct,
    NotificationLog,
    PriceHistory,
    ProductListing,
    SiteConfig,
    User,
    WatchlistItem,
)
from app.db.session import create_db_engine, init_db


def test_init_db_creates_all_eight_tables(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "SNAPSHOTS_DIR", tmp_path / "snapshots")
    db_file = tmp_path / "schema_check.db"
    engine = create_db_engine(f"sqlite:///{db_file}")
    try:
        init_db(engine)
        table_names = set(inspect(engine).get_table_names())
        expected = {
            "users",
            "canonical_products",
            "product_listings",
            "price_history",
            "watchlist_items",
            "adapter_run_logs",
            "site_configs",
            "notification_logs",
        }
        assert expected.issubset(table_names)
    finally:
        engine.dispose()


def test_sqlite_foreign_keys_pragma_enabled(db_session: Session) -> None:
    pragma_value = db_session.execute(text("PRAGMA foreign_keys")).scalar_one()
    assert pragma_value == 1

    orphan_listing = ProductListing(
        canonical_product_id=999999,
        store="jdsports",
        url="https://www.jdsports.ro/orphan-product",
        current_price=499.99,
        raw_title="Orphan Sneaker",
    )
    db_session.add(orphan_listing)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_unique_constraints_enforced(db_session: Session) -> None:
    user1 = User(email="dup@pricemonitor.local", password_hash="hash1", role="user")
    db_session.add(user1)
    db_session.commit()

    db_session.add(User(email="dup@pricemonitor.local", password_hash="hash2", role="user"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    prod1 = CanonicalProduct(name="Nike Dunk Low", brand="Nike", sku="DD1391-100")
    db_session.add(prod1)
    db_session.commit()

    db_session.add(CanonicalProduct(name="Duplicate SKU", brand="Nike", sku="DD1391-100"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    listing1 = ProductListing(
        canonical_product_id=prod1.id,
        store="jdsports",
        url="https://www.jdsports.ro/nike-dunk-low-dd1391-100",
        current_price=549.99,
        raw_title="Nike Dunk Low Panda",
    )
    db_session.add(listing1)
    db_session.commit()

    db_session.add(
        ProductListing(
            canonical_product_id=prod1.id,
            store="sizeer",
            url="https://www.jdsports.ro/nike-dunk-low-dd1391-100",
            current_price=539.99,
            raw_title="Duplicate URL",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    db_session.add(SiteConfig(store="jdsports"))
    db_session.commit()
    db_session.add(SiteConfig(store="jdsports"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    db_session.add(WatchlistItem(user_id=user1.id, canonical_product_id=prod1.id))
    db_session.commit()
    db_session.add(WatchlistItem(user_id=user1.id, canonical_product_id=prod1.id))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_cascade_delete_canonical_product_removes_listings_history_and_watchlist(
    db_session: Session,
) -> None:
    user = User(email="cascade_prod@pricemonitor.local", password_hash="hash", role="user")
    product = CanonicalProduct(name="Adidas Samba OG", brand="Adidas", sku="B75806")
    db_session.add_all([user, product])
    db_session.flush()

    listing = ProductListing(
        canonical_product_id=product.id,
        store="sizeer",
        url="https://sizeer.ro/adidas-samba-og-b75806",
        current_price=529.99,
        raw_title="Adidas Samba OG White",
    )
    watchlist = WatchlistItem(user_id=user.id, canonical_product_id=product.id, target_price=450.0)
    db_session.add_all([listing, watchlist])
    db_session.flush()

    history = PriceHistory(
        product_listing_id=listing.id,
        price=529.99,
        currency="RON",
        in_stock=True,
        status="valid",
    )
    db_session.add(history)
    db_session.commit()

    db_session.delete(product)
    db_session.commit()

    assert db_session.query(ProductListing).count() == 0
    assert db_session.query(PriceHistory).count() == 0
    assert db_session.query(WatchlistItem).count() == 0
    assert db_session.query(User).count() == 1


def test_cascade_delete_user_removes_watchlist_and_notifications(
    db_session: Session,
) -> None:
    user = User(email="cascade_user@pricemonitor.local", password_hash="hash", role="user")
    product = CanonicalProduct(name="New Balance 550", brand="New Balance", sku="BB550WT1")
    db_session.add_all([user, product])
    db_session.flush()

    listing = ProductListing(
        canonical_product_id=product.id,
        store="buzzsneakers",
        url="https://www.buzzsneakers.ro/new-balance-550-bb550wt1",
        current_price=599.99,
        raw_title="New Balance 550 White/Green",
    )
    watchlist = WatchlistItem(user_id=user.id, canonical_product_id=product.id)
    db_session.add_all([listing, watchlist])
    db_session.flush()

    notif = NotificationLog(
        user_id=user.id,
        product_listing_id=listing.id,
        channel="email",
        trigger_reason="price_drop",
        message_payload="Pret scazut la 599.99 RON",
    )
    db_session.add(notif)
    db_session.commit()

    db_session.delete(user)
    db_session.commit()

    assert db_session.query(WatchlistItem).count() == 0
    assert db_session.query(NotificationLog).count() == 0
    assert db_session.query(ProductListing).count() == 1


def test_optional_image_url_on_canonical_product_and_listing(db_session: Session) -> None:
    product_no_img = CanonicalProduct(
        name="Puma Palermo",
        brand="Puma",
        sku="396463-01",
        image_url=None,
    )
    product_with_img = CanonicalProduct(
        name="Nike Air Max 90",
        brand="Nike",
        sku="CN8490-100",
        image_url="https://www.jdsports.ro/media/catalog/product/cn8490-100.jpg",
    )
    db_session.add_all([product_no_img, product_with_img])
    db_session.flush()

    listing_no_img = ProductListing(
        canonical_product_id=product_no_img.id,
        store="jdsports",
        url="https://www.jdsports.ro/puma-palermo-396463-01",
        current_price=449.99,
        raw_title="Puma Palermo",
        image_url=None,
    )
    listing_with_img = ProductListing(
        canonical_product_id=product_with_img.id,
        store="sizeer",
        url="https://sizeer.ro/nike-air-max-90-cn8490-100",
        current_price=649.99,
        raw_title="Nike Air Max 90 Triple White",
        image_url="https://sizeer.ro/media/catalog/product/cn8490-100.jpg",
    )
    db_session.add_all([listing_no_img, listing_with_img])
    db_session.commit()

    assert product_no_img.image_url is None
    assert listing_no_img.image_url is None
    assert product_with_img.image_url is not None
    assert listing_with_img.image_url is not None


def test_site_config_and_adapter_run_log_defaults(db_session: Session) -> None:
    cfg = SiteConfig(store="buzzsneakers")
    run_log = AdapterRunLog(
        store="buzzsneakers",
        status="suspect",
        error_message="Price drop >70%",
        snapshot_path="storage/snapshots/buzzsneakers_20261125.html",
        duration_ms=420,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add_all([cfg, run_log])
    db_session.commit()
    db_session.refresh(cfg)
    db_session.refresh(run_log)

    assert cfg.polling_interval_minutes == 360
    assert cfg.min_delay_seconds == 10
    assert cfg.max_requests_per_hour == 30
    assert cfg.circuit_breaker_open is False
    assert run_log.status == "suspect"
    assert run_log.snapshot_path == "storage/snapshots/buzzsneakers_20261125.html"


def test_utc_datetime_roundtrip_preserves_timezone_awareness(db_session: Session) -> None:
    cfg = SiteConfig(store="jdsports")
    db_session.add(cfg)
    db_session.commit()
    db_session.expire_all()

    loaded = db_session.get(SiteConfig, cfg.id)
    assert loaded is not None
    assert loaded.updated_at.tzinfo == timezone.utc
    delta = utcnow() - loaded.updated_at
    assert delta.total_seconds() >= 0


def test_numeric_precision_and_nullable_price_history_error(db_session: Session) -> None:
    product = CanonicalProduct(name="Nike Dunk Low Retro", brand="Nike", sku="DD1391-101")
    db_session.add(product)
    db_session.flush()

    listing = ProductListing(
        canonical_product_id=product.id,
        store="jdsports",
        url="https://www.jdsports.ro/nike-dunk-low-dd1391-101",
        current_price=Decimal("489.99"),
        original_price=Decimal("599.99"),
        raw_title="Nike Dunk Low Retro",
    )
    db_session.add(listing)
    db_session.flush()

    error_entry = PriceHistory(
        product_listing_id=listing.id,
        price=None,
        currency="RON",
        in_stock=False,
        status="error",
    )
    db_session.add(error_entry)
    db_session.commit()
    db_session.expire_all()

    loaded_listing = db_session.get(ProductListing, listing.id)
    loaded_history = db_session.get(PriceHistory, error_entry.id)
    assert loaded_listing is not None and loaded_listing.current_price == Decimal("489.99")
    assert isinstance(loaded_listing.current_price, Decimal)
    assert loaded_history is not None and loaded_history.price is None
    assert loaded_history.status == "error"


def test_unique_listing_per_canonical_product_and_store(db_session: Session) -> None:
    product = CanonicalProduct(name="Adidas Gazelle", brand="Adidas", sku="BB5476")
    db_session.add(product)
    db_session.flush()

    db_session.add(
        ProductListing(
            canonical_product_id=product.id,
            store="sizeer",
            url="https://sizeer.ro/adidas-gazelle-bb5476-v1",
            current_price=Decimal("499.99"),
            raw_title="Adidas Gazelle",
        )
    )
    db_session.commit()

    db_session.add(
        ProductListing(
            canonical_product_id=product.id,
            store="sizeer",
            url="https://sizeer.ro/adidas-gazelle-bb5476-v2",
            current_price=Decimal("489.99"),
            raw_title="Adidas Gazelle Duplicate Store",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_check_constraints_reject_invalid_enums_and_politeness_bounds(
    db_session: Session,
) -> None:
    invalid_records = [
        User(email="badrole@pricemonitor.local", password_hash="hash", role="superadmin"),
        SiteConfig(store="zara"),
        SiteConfig(store="jdsports", min_delay_seconds=5),
        SiteConfig(store="sizeer", max_requests_per_hour=60),
        SiteConfig(store="buzzsneakers", polling_interval_minutes=0),
        AdapterRunLog(store="jdsports", status="unknown"),
    ]
    for record in invalid_records:
        db_session.add(record)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()


def test_cascade_delete_product_listing_removes_history_and_nulls_notification_log(
    db_session: Session,
) -> None:
    user = User(email="notif_keep@pricemonitor.local", password_hash="hash", role="user")
    product = CanonicalProduct(name="ASICS Gel-1130", brand="ASICS", sku="1201A256-113")
    db_session.add_all([user, product])
    db_session.flush()

    listing = ProductListing(
        canonical_product_id=product.id,
        store="buzzsneakers",
        url="https://www.buzzsneakers.ro/asics-gel-1130",
        current_price=Decimal("499.99"),
        raw_title="ASICS Gel-1130",
    )
    db_session.add(listing)
    db_session.flush()

    history = PriceHistory(
        product_listing_id=listing.id,
        price=Decimal("499.99"),
        status="valid",
    )
    notif = NotificationLog(
        user_id=user.id,
        product_listing_id=listing.id,
        channel="telegram",
        trigger_reason="back_in_stock",
        message_payload="Produsul a revenit in stoc!",
    )
    db_session.add_all([history, notif])
    db_session.commit()
    notif_id = notif.id

    db_session.delete(listing)
    db_session.commit()
    db_session.expire_all()

    assert db_session.query(PriceHistory).count() == 0
    preserved_notif = db_session.get(NotificationLog, notif_id)
    assert preserved_notif is not None
    assert preserved_notif.product_listing_id is None
    assert preserved_notif.message_payload == "Produsul a revenit in stoc!"
