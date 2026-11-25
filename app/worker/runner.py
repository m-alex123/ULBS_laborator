"""Polite scheduled scrape cycle runner and CLI entrypoint."""

import argparse
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import sys
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import utcnow
from app.db.models import ProductListing, SiteConfig
from app.db.session import SessionLocal, init_db
from app.scraping.adapters import get_adapter
from app.scraping.drift_detector import record_scrape_outcome
from app.scraping.polite_client import (
    CircuitBreakerOpenError,
    HourlyRateLimitExceededError,
    PoliteClientError,
    PoliteHttpClient,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ScrapeCycleSummary:
    """Counters summarizing one polite scrape cycle across active listings."""

    total_listings: int = 0
    processed: int = 0
    succeeded: int = 0
    suspect: int = 0
    failed: int = 0
    skipped_circuit_breaker: int = 0
    skipped_rate_limit: int = 0
    skipped_not_due: int = 0


def _is_due(listing: ProductListing, interval_minutes: int, now: datetime) -> bool:
    if listing.last_checked_at is None:
        return True
    return listing.last_checked_at <= now - timedelta(minutes=interval_minutes)


def run_scrape_cycle(
    db: Session,
    *,
    polite_client: PoliteHttpClient | None = None,
    force: bool = False,
    now: datetime | None = None,
) -> ScrapeCycleSummary:
    """Iterate active ProductListings respectfully through PoliteHttpClient and drift detection."""
    current_time = now or utcnow()
    owns_client = polite_client is None
    client = polite_client or PoliteHttpClient()
    summary = ScrapeCycleSummary()

    try:
        configs = {
            cfg.store: cfg
            for cfg in db.scalars(select(SiteConfig)).all()
        }
        listings = db.scalars(
            select(ProductListing)
            .where(ProductListing.is_active.is_(True))
            .order_by(ProductListing.id.asc())
        ).all()
        summary.total_listings = len(listings)

        for listing in listings:
            cfg = configs.get(listing.store)
            if cfg is None:
                cfg = SiteConfig(store=listing.store)
                db.add(cfg)
                db.flush()
                configs[listing.store] = cfg

            if cfg.circuit_breaker_open:
                summary.skipped_circuit_breaker += 1
                continue

            if not force and not _is_due(listing, cfg.polling_interval_minutes, current_time):
                summary.skipped_not_due += 1
                continue

            started = time.monotonic()
            try:
                response = client.fetch(
                    listing.url,
                    min_delay_seconds=cfg.min_delay_seconds,
                    max_requests_per_hour=cfg.max_requests_per_hour,
                    circuit_breaker_open=cfg.circuit_breaker_open,
                )
            except CircuitBreakerOpenError:
                summary.skipped_circuit_breaker += 1
                continue
            except HourlyRateLimitExceededError:
                summary.skipped_rate_limit += 1
                continue
            except PoliteClientError as exc:
                duration_ms = int((time.monotonic() - started) * 1000)
                record_scrape_outcome(
                    db,
                    listing=listing,
                    scraped=None,
                    error_message=str(exc),
                    duration_ms=duration_ms,
                )
                summary.processed += 1
                summary.failed += 1
                continue

            duration_ms = int((time.monotonic() - started) * 1000)
            adapter = get_adapter(listing.store)
            scraped = adapter.parse(response.text, listing.url)
            outcome = record_scrape_outcome(
                db,
                listing=listing,
                scraped=scraped,
                raw_html=response.text,
                duration_ms=duration_ms,
            )
            summary.processed += 1
            if outcome.status == "valid":
                summary.succeeded += 1
            elif outcome.status == "suspect":
                summary.suspect += 1
            else:
                summary.failed += 1

        db.commit()
    finally:
        if owns_client:
            client.close()

    return summary


async def run_background_worker_loop(stop_event: asyncio.Event) -> None:
    """Periodic background loop enabled only when settings.ENABLE_BACKGROUND_WORKER=True."""
    client = PoliteHttpClient()
    try:
        while not stop_event.is_set():
            try:
                def _tick() -> ScrapeCycleSummary:
                    with SessionLocal() as session:
                        return run_scrape_cycle(session, polite_client=client, force=False)

                await asyncio.to_thread(_tick)
            except Exception:  # pragma: no cover - defensive loop guard
                logger.exception("Background scrape cycle failed")

            try:
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=float(settings.WORKER_LOOP_SLEEP_SECONDS),
                )
            except asyncio.TimeoutError:
                continue
    finally:
        client.close()


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint supporting `python -m app.worker.runner --once`."""
    parser = argparse.ArgumentParser(description="P23 Ethical Scraper Worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single forced scrape cycle across active listings and exit.",
    )
    args = parser.parse_args(argv)

    init_db()
    if args.once or True:
        with SessionLocal() as session:
            summary = run_scrape_cycle(session, force=True)
        print(
            f"Worker cycle done: total={summary.total_listings} "
            f"processed={summary.processed} ok={summary.succeeded} "
            f"suspect={summary.suspect} failed={summary.failed} "
            f"cb_skipped={summary.skipped_circuit_breaker}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
