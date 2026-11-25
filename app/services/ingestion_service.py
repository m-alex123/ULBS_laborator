"""Ethical URL ingestion service connecting POST /watchlist to Step 3 scraping."""

from decimal import Decimal
import time
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    AdapterRunLog,
    CanonicalProduct,
    ProductListing,
    SiteConfig,
    WatchlistItem,
)
from app.scraping.adapters import get_adapter_for_url
from app.scraping.deduplicator import upsert_scraped_listing
from app.scraping.drift_detector import (
    check_plausibility,
    record_scrape_outcome,
    save_failure_snapshot,
)
from app.scraping.polite_client import PoliteClientError, PoliteHttpClient


class WatchlistIngestionError(ValueError):
    """Raised when a submitted URL fails validation, politeness checks, or plausibility."""


def ingest_product_url(
    db: Session,
    *,
    user_id: int,
    url: str,
    target_price: Decimal | None = None,
    polite_client: PoliteHttpClient,
) -> tuple[CanonicalProduct, WatchlistItem]:
    """Validate URL, reuse or politely scrape/deduplicate listing, and attach WatchlistItem."""
    cleaned_url = url.strip()
    parsed = urlparse(cleaned_url)
    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
        raise WatchlistIngestionError("Introdu un URL valid (http:// sau https://).")

    try:
        adapter = get_adapter_for_url(cleaned_url)
    except ValueError as exc:
        raise WatchlistIngestionError(
            "Domeniu nesuportat. Sunt acceptate doar URL-uri de pe jdsports.ro, sizeer.ro și buzzsneakers.ro."
        ) from exc

    existing_listing = db.scalar(
        select(ProductListing)
        .where(ProductListing.url == cleaned_url)
        .options(selectinload(ProductListing.canonical_product))
    )

    canonical: CanonicalProduct
    if existing_listing is not None:
        canonical = existing_listing.canonical_product
    else:
        cfg = db.scalar(select(SiteConfig).where(SiteConfig.store == adapter.store))
        if cfg is None:
            cfg = SiteConfig(store=adapter.store)
            db.add(cfg)
            db.flush()

        started = time.monotonic()
        try:
            response = polite_client.fetch(
                cleaned_url,
                min_delay_seconds=cfg.min_delay_seconds,
                max_requests_per_hour=cfg.max_requests_per_hour,
                circuit_breaker_open=cfg.circuit_breaker_open,
            )
        except PoliteClientError as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            db.add(
                AdapterRunLog(
                    store=adapter.store,
                    status="failed",
                    error_message=str(exc),
                    snapshot_path=None,
                    duration_ms=duration_ms,
                )
            )
            db.commit()
            raise WatchlistIngestionError(
                f"Nu am putut prelua pagina respectând politica etică ({exc})."
            ) from exc

        duration_ms = int((time.monotonic() - started) * 1000)
        scraped = adapter.parse(response.text, cleaned_url)
        drift = check_plausibility(scraped)
        if not drift.is_valid:
            snapshot_path = save_failure_snapshot(
                adapter.store,
                response.text,
                reason=drift.reasons[0] if drift.reasons else "suspect",
            )
            cfg.adapter_status = "suspect"
            db.add(
                AdapterRunLog(
                    store=adapter.store,
                    status="suspect",
                    error_message="; ".join(drift.reasons),
                    snapshot_path=snapshot_path,
                    duration_ms=duration_ms,
                )
            )
            db.commit()
            raise WatchlistIngestionError(
                "Pagina preluată a declanșat verificarea de derivă (date lipsă sau preț invalid)."
            )

        listing, dedup = upsert_scraped_listing(db, scraped)
        record_scrape_outcome(
            db,
            listing=listing,
            scraped=scraped,
            raw_html=response.text,
            duration_ms=duration_ms,
        )
        canonical = dedup.canonical_product

    watchlist_item = db.scalar(
        select(WatchlistItem).where(
            WatchlistItem.user_id == user_id,
            WatchlistItem.canonical_product_id == canonical.id,
        )
    )
    if watchlist_item is None:
        watchlist_item = WatchlistItem(
            user_id=user_id,
            canonical_product_id=canonical.id,
            target_price=target_price,
        )
        db.add(watchlist_item)
    elif target_price is not None:
        watchlist_item.target_price = target_price

    db.commit()
    db.refresh(canonical)
    db.refresh(watchlist_item)
    return canonical, watchlist_item
