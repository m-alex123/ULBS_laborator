from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import httpx
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base, utcnow
from app.db.models import (
    AdapterRunLog,
    CanonicalProduct,
    NotificationLog,
    PriceHistory,
    ProductListing,
    SiteConfig,
)
from app.db.session import create_db_engine
from app.scraping.polite_client import PoliteHttpClient
from app.worker.runner import ScrapeCycleSummary, main as worker_main, run_scrape_cycle

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _make_worker_client(responses_by_host_path: dict[tuple[str, str], httpx.Response]) -> PoliteHttpClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        resp = responses_by_host_path.get((request.url.host, request.url.path))
        return resp if resp is not None else httpx.Response(404, text="Not found")

    now = [1000.0]

    def fake_clock() -> float:
        return now[0]

    def fake_sleep(sec: float) -> None:
        now[0] += sec

    return PoliteHttpClient(
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        clock=fake_clock,
        sleep_fn=fake_sleep,
    )


def test_run_scrape_cycle_updates_valid_marks_suspect_and_skips_open_cb(
    db_session: Session,
) -> None:
    now = utcnow()
    jd_cfg = SiteConfig(store="jdsports", circuit_breaker_open=False, adapter_status="healthy")
    sizeer_cfg = SiteConfig(store="sizeer", circuit_breaker_open=False, adapter_status="healthy")
    buzz_cfg = SiteConfig(store="buzzsneakers", circuit_breaker_open=True, adapter_status="circuit_open")

    prod = CanonicalProduct(
        name="Nike Air Jordan 1 Low 'University Blue'",
        brand="Nike",
        sku="553558-403",
    )
    db_session.add_all([jd_cfg, sizeer_cfg, buzz_cfg, prod])
    db_session.flush()

    jd_listing = ProductListing(
        canonical_product_id=prod.id,
        store="jdsports",
        url="https://www.jdsports.ro/nike-air-jordan-1-low-university-blue-553558-403",
        current_price=Decimal("529.99"),
        original_price=Decimal("599.99"),
        raw_title="Nike Air Jordan 1 Low 'University Blue' Bărbați",
        in_stock=True,
        last_checked_at=now - timedelta(hours=7),
    )
    sizeer_listing = ProductListing(
        canonical_product_id=prod.id,
        store="sizeer",
        url="https://sizeer.ro/nike-air-jordan-1-low-553558-403",
        current_price=Decimal("529.99"),
        original_price=Decimal("599.99"),
        raw_title="Jordan Air 1 Low University Blue 553558-403",
        in_stock=True,
        last_checked_at=now - timedelta(hours=7),
    )
    buzz_listing = ProductListing(
        canonical_product_id=prod.id,
        store="buzzsneakers",
        url="https://www.buzzsneakers.ro/pantofi-sport/nike-air-jordan-1-low-553558-403",
        current_price=Decimal("519.99"),
        original_price=Decimal("599.99"),
        raw_title="Nike Pantofi sport Air Jordan 1 Low 553558-403",
        in_stock=True,
        last_checked_at=now - timedelta(hours=7),
    )
    db_session.add_all([jd_listing, sizeer_listing, buzz_listing])
    db_session.commit()

    valid_jd_html = (FIXTURES_DIR / "jdsports_product.html").read_text(encoding="utf-8")
    broken_sizeer_html = (
        (FIXTURES_DIR / "sizeer_product.html")
        .read_text(encoding="utf-8")
        .replace("m-productPrice_promo", "broken-promo-selector")
    )

    polite_client = _make_worker_client(
        {
            ("www.jdsports.ro", "/nike-air-jordan-1-low-university-blue-553558-403"): httpx.Response(
                200, text=valid_jd_html
            ),
            ("sizeer.ro", "/nike-air-jordan-1-low-553558-403"): httpx.Response(
                200, text=broken_sizeer_html
            ),
        }
    )

    summary = run_scrape_cycle(db_session, polite_client=polite_client)
    assert isinstance(summary, ScrapeCycleSummary)
    assert summary.total_listings == 3
    assert summary.succeeded == 1
    assert summary.suspect == 1
    assert summary.skipped_circuit_breaker == 1
    assert summary.failed == 0

    db_session.refresh(jd_cfg)
    db_session.refresh(sizeer_cfg)
    db_session.refresh(jd_listing)
    db_session.refresh(sizeer_listing)

    assert jd_cfg.adapter_status == "healthy"
    assert jd_listing.current_price == Decimal("489.99")
    assert sizeer_cfg.adapter_status == "suspect"
    # Preserved valid price, zero false user alerts
    assert sizeer_listing.current_price == Decimal("529.99")
    assert db_session.query(NotificationLog).count() == 0
    assert (
        db_session.query(PriceHistory)
        .filter_by(product_listing_id=sizeer_listing.id, status="suspect")
        .count()
        == 1
    )
    suspect_log = (
        db_session.query(AdapterRunLog).filter_by(store="sizeer", status="suspect").one()
    )
    assert suspect_log.snapshot_path is not None


def test_run_scrape_cycle_skips_listings_not_due_unless_forced(db_session: Session) -> None:
    now = utcnow()
    cfg = SiteConfig(store="jdsports", polling_interval_minutes=360)
    prod = CanonicalProduct(name="Nike Dunk Low", brand="Nike", sku="DD1391-100")
    db_session.add_all([cfg, prod])
    db_session.flush()
    db_session.add(
        ProductListing(
            canonical_product_id=prod.id,
            store="jdsports",
            url="https://www.jdsports.ro/nike-dunk-low-dd1391-100",
            current_price=Decimal("549.99"),
            raw_title="Nike Dunk Low",
            in_stock=True,
            last_checked_at=now - timedelta(minutes=30),
        )
    )
    db_session.commit()

    polite_client = _make_worker_client({})
    summary = run_scrape_cycle(db_session, polite_client=polite_client, force=False)
    assert summary.skipped_not_due == 1
    assert summary.processed == 0


def test_worker_cli_once_runs_cleanly(tmp_path, monkeypatch) -> None:
    import app.worker.runner as runner_mod

    db_path = tmp_path / "worker_cli.db"
    engine = create_db_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    monkeypatch.setattr(runner_mod, "SessionLocal", TestSession)
    monkeypatch.setattr(runner_mod, "init_db", lambda: None)

    try:
        exit_code = worker_main(["--once"])
        assert exit_code == 0
    finally:
        engine.dispose()


def test_background_worker_disabled_by_default_in_settings() -> None:
    assert settings.ENABLE_BACKGROUND_WORKER is False
