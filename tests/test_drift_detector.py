from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
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
from app.scraping.adapters import get_adapter
from app.scraping.adapters.base import ScrapedProductData
from app.scraping.drift_detector import (
    check_plausibility,
    compute_title_similarity,
    record_scrape_outcome,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _make_scraped(
    *,
    title: str = "Nike Air Jordan 1 Low 'University Blue' Bărbați",
    current_price: Decimal | None = Decimal("489.99"),
    original_price: Decimal | None = Decimal("599.99"),
    currency: str = "RON",
    in_stock: bool | None = True,
) -> ScrapedProductData:
    return ScrapedProductData(
        store="jdsports",
        url="https://www.jdsports.ro/nike-air-jordan-1-low-university-blue-553558-403",
        title=title,
        current_price=current_price,
        original_price=original_price,
        currency=currency,
        in_stock=in_stock,
        image_url="https://www.jdsports.ro/media/catalog/product/cache/nike.jpg",
        sku="553558-403",
        brand="Nike",
    )


def test_plausibility_flags_extreme_drop_rise_low_price_title_mismatch_and_missing_fields() -> None:
    prev_title = "Nike Air Jordan 1 Low 'University Blue' Bărbați"
    prev_price = Decimal("500.00")

    # >95% drop (also violates >70% D-002 threshold)
    drop_96 = check_plausibility(
        _make_scraped(current_price=Decimal("19.99")),
        previous_title=prev_title,
        previous_price=prev_price,
    )
    assert drop_96.is_valid is False
    assert drop_96.status == "suspect"

    # 80% drop (validates D-002 >70% threshold even if price >= 50 RON)
    drop_80 = check_plausibility(
        _make_scraped(current_price=Decimal("90.00")),
        previous_title=prev_title,
        previous_price=prev_price,
    )
    assert drop_80.is_valid is False

    # >200% rise
    rise_250 = check_plausibility(
        _make_scraped(current_price=Decimal("1800.00")),
        previous_title=prev_title,
        previous_price=prev_price,
    )
    assert rise_250.is_valid is False

    # Zero / negative / < 50 RON
    for bad_price in (Decimal("0.00"), Decimal("-10.00"), Decimal("49.00")):
        res = check_plausibility(
            _make_scraped(current_price=bad_price),
            previous_title=prev_title,
            previous_price=Decimal("100.00"),
        )
        assert res.is_valid is False

    # Title mismatch < 60%
    assert compute_title_similarity(prev_title, "404 Pagina nu a fost găsită") < 0.60
    title_res = check_plausibility(
        _make_scraped(title="404 Pagina nu a fost găsită"),
        previous_title=prev_title,
        previous_price=prev_price,
    )
    assert title_res.is_valid is False

    # Missing required fields
    missing_price = check_plausibility(_make_scraped(current_price=None))
    missing_title = check_plausibility(_make_scraped(title=None))
    missing_stock = check_plausibility(_make_scraped(in_stock=None))
    assert not missing_price.is_valid
    assert not missing_title.is_valid
    assert not missing_stock.is_valid


def test_breaking_selector_marks_adapter_suspect_saves_snapshot_and_suppresses_user_alerts(
    db_session: Session,
) -> None:
    user = User(email="watcher@pricemonitor.local", password_hash="hash", role="user")
    cfg = SiteConfig(store="jdsports", adapter_status="healthy")
    product = CanonicalProduct(
        name="Nike Air Jordan 1 Low 'University Blue'",
        brand="Nike",
        sku="553558-403",
    )
    db_session.add_all([user, cfg, product])
    db_session.flush()

    listing = ProductListing(
        canonical_product_id=product.id,
        store="jdsports",
        url="https://www.jdsports.ro/nike-air-jordan-1-low-university-blue-553558-403",
        current_price=Decimal("489.99"),
        original_price=Decimal("599.99"),
        raw_title="Nike Air Jordan 1 Low 'University Blue' Bărbați",
        in_stock=True,
    )
    watchlist = WatchlistItem(
        user_id=user.id,
        canonical_product_id=product.id,
        target_price=Decimal("470.00"),
        notify_email=True,
    )
    db_session.add_all([listing, watchlist])
    db_session.commit()

    # Simulate retailer HTML DOM redesign breaking the price selector (e.g., class renamed)
    valid_html = (FIXTURES_DIR / "jdsports_product.html").read_text(encoding="utf-8")
    broken_html = valid_html.replace('class="current-price"', 'class="redesigned-price-tag"')
    broken_html = broken_html.replace('class="old-price"', 'class="redesigned-old-tag"')

    adapter = get_adapter("jdsports")
    scraped = adapter.parse(broken_html, listing.url)
    outcome = record_scrape_outcome(
        db_session,
        listing=listing,
        scraped=scraped,
        raw_html=broken_html,
        duration_ms=145,
    )
    db_session.commit()
    db_session.refresh(cfg)
    db_session.refresh(listing)

    assert outcome.status == "suspect"
    assert outcome.should_notify_users is False
    assert cfg.adapter_status == "suspect"

    # Last valid price preserved on ProductListing
    assert listing.current_price == Decimal("489.99")

    # Snapshot saved inside isolated SNAPSHOTS_DIR and referenced in AdapterRunLog
    run_log = db_session.query(AdapterRunLog).filter_by(store="jdsports").one()
    assert run_log.status == "suspect"
    assert run_log.snapshot_path is not None
    snapshot_file = Path(run_log.snapshot_path)
    if not snapshot_file.is_absolute():
        snapshot_file = settings.SNAPSHOTS_DIR / snapshot_file.name
    assert snapshot_file.exists()
    assert "redesigned-price-tag" in snapshot_file.read_text(encoding="utf-8")

    # Suspect PriceHistory recorded, and ZERO false user alerts generated
    history = db_session.query(PriceHistory).filter_by(product_listing_id=listing.id).one()
    assert history.status == "suspect"
    assert db_session.query(NotificationLog).count() == 0


def test_valid_scrape_updates_listing_records_history_and_keeps_healthy_status(
    db_session: Session,
) -> None:
    cfg = SiteConfig(store="jdsports", adapter_status="suspect")
    product = CanonicalProduct(name="Nike Air Jordan 1 Low", brand="Nike", sku="553558-403")
    db_session.add_all([cfg, product])
    db_session.flush()

    listing = ProductListing(
        canonical_product_id=product.id,
        store="jdsports",
        url="https://www.jdsports.ro/nike-air-jordan-1-low-university-blue-553558-403",
        current_price=Decimal("529.99"),
        original_price=Decimal("599.99"),
        raw_title="Nike Air Jordan 1 Low 'University Blue' Bărbați",
        in_stock=True,
    )
    db_session.add(listing)
    db_session.commit()

    valid_html = (FIXTURES_DIR / "jdsports_product.html").read_text(encoding="utf-8")
    scraped = get_adapter("jdsports").parse(valid_html, listing.url)
    outcome = record_scrape_outcome(
        db_session,
        listing=listing,
        scraped=scraped,
        raw_html=valid_html,
        duration_ms=110,
    )
    db_session.commit()
    db_session.refresh(cfg)
    db_session.refresh(listing)

    assert outcome.status == "valid"
    assert outcome.should_notify_users is True
    assert outcome.snapshot_path is None
    assert cfg.adapter_status == "healthy"
    assert listing.current_price == Decimal("489.99")
