"""P23 Drift Detection, HTML snapshot persistence, and scrape outcome recording."""

from dataclasses import dataclass, field
from decimal import Decimal
from difflib import SequenceMatcher
from pathlib import Path
import re
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import PROJECT_ROOT, settings
from app.db.base import utcnow
from app.db.models import AdapterRunLog, PriceHistory, ProductListing, SiteConfig
from app.scraping.adapters.base import ScrapedProductData
from app.scraping.price_parser import strip_diacritics


@dataclass(frozen=True, slots=True)
class DriftCheckResult:
    """Result of evaluating plausibility rules against a scraped product payload."""

    is_valid: bool
    status: Literal["valid", "suspect"]
    reasons: list[str] = field(default_factory=list)
    title_similarity: float | None = None
    price_change_percent: float | None = None


@dataclass(frozen=True, slots=True)
class ScrapeOutcome:
    """Persisted outcome of a scrape run, explicitly controlling user alert eligibility."""

    status: Literal["valid", "suspect", "failed"]
    drift_result: DriftCheckResult | None
    snapshot_path: str | None
    should_notify_users: bool


def _normalize_for_similarity(text: str) -> str:
    folded = strip_diacritics(text).lower()
    return " ".join(re.findall(r"[a-z0-9]+", folded))


def compute_title_similarity(previous_title: str, current_title: str) -> float:
    """Compute normalized similarity ratio in [0.0, 1.0] between previous and current titles."""
    norm_prev = _normalize_for_similarity(previous_title)
    norm_curr = _normalize_for_similarity(current_title)
    if not norm_prev or not norm_curr:
        return 0.0
    return SequenceMatcher(None, norm_prev, norm_curr).ratio()


def check_plausibility(
    scraped: ScrapedProductData,
    *,
    previous_title: str | None = None,
    previous_price: Decimal | None = None,
) -> DriftCheckResult:
    """Evaluate D-002 plausibility thresholds to detect broken selectors or layout drift."""
    reasons: list[str] = []
    title_sim: float | None = None
    price_change_pct: float | None = None

    if not scraped.title or not scraped.title.strip():
        reasons.append("missing_title")
    if scraped.current_price is None:
        reasons.append("missing_price")
    if not scraped.currency:
        reasons.append("missing_currency")
    elif scraped.currency.strip().upper() != "RON":
        reasons.append(f"unexpected_currency_{scraped.currency.strip().upper()}")
    if scraped.in_stock is None:
        reasons.append("missing_stock_status")

    min_valid_price = Decimal(str(settings.DRIFT_MIN_VALID_PRICE_RON))
    if scraped.current_price is not None:
        if scraped.current_price <= Decimal("0.00"):
            reasons.append("non_positive_price")
        elif scraped.current_price < min_valid_price:
            reasons.append(f"price_below_minimum_{min_valid_price}_RON")

        if previous_price is not None and previous_price > Decimal("0.00"):
            delta_pct = float(((scraped.current_price - previous_price) / previous_price) * 100)
            price_change_pct = round(delta_pct, 2)
            if delta_pct < -settings.DRIFT_MAX_DROP_PERCENT:
                reasons.append(f"extreme_price_drop_{abs(price_change_pct):.1f}%")
            elif delta_pct > settings.DRIFT_MAX_RISE_PERCENT:
                reasons.append(f"extreme_price_rise_{price_change_pct:.1f}%")

    if previous_title and scraped.title:
        title_sim = round(compute_title_similarity(previous_title, scraped.title), 4)
        if title_sim < settings.DRIFT_MIN_TITLE_SIMILARITY:
            reasons.append(f"title_similarity_below_{settings.DRIFT_MIN_TITLE_SIMILARITY:.2f}")

    is_valid = len(reasons) == 0
    return DriftCheckResult(
        is_valid=is_valid,
        status="valid" if is_valid else "suspect",
        reasons=reasons,
        title_similarity=title_sim,
        price_change_percent=price_change_pct,
    )


def save_failure_snapshot(
    store: str,
    raw_html: str,
    reason: str = "drift",
    snapshots_dir: Path | None = None,
) -> str:
    """Persist failed or suspect HTML snapshot to storage/snapshots and return stored path."""
    target_dir = snapshots_dir or settings.SNAPSHOTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    ts = utcnow().strftime("%Y%m%dT%H%M%S%fZ")
    slug = re.sub(r"[^a-z0-9]+", "-", reason.lower()).strip("-")[:32] or "snapshot"
    file_path = target_dir / f"{store}_{ts}_{slug}.html"
    file_path.write_text(raw_html, encoding="utf-8")

    try:
        return str(file_path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except ValueError:
        return str(file_path)


def _get_or_create_site_config(db: Session, store: str) -> SiteConfig:
    cfg = db.scalar(select(SiteConfig).where(SiteConfig.store == store))
    if cfg is None:
        cfg = SiteConfig(store=store)
        db.add(cfg)
        db.flush()
    return cfg


def record_scrape_outcome(
    db: Session,
    *,
    listing: ProductListing,
    scraped: ScrapedProductData | None,
    raw_html: str = "",
    duration_ms: int = 0,
    error_message: str | None = None,
    snapshots_dir: Path | None = None,
) -> ScrapeOutcome:
    """Validate scraped data, update SiteConfig/AdapterRunLog/PriceHistory, and gate user alerts."""
    cfg = _get_or_create_site_config(db, listing.store)
    now = utcnow()

    if scraped is None:
        snapshot_path = (
            save_failure_snapshot(
                listing.store,
                raw_html,
                reason=error_message or "fetch_failed",
                snapshots_dir=snapshots_dir,
            )
            if raw_html
            else None
        )
        cfg.adapter_status = "degraded"
        db.add(
            AdapterRunLog(
                store=listing.store,
                status="failed",
                error_message=error_message or "Scrape fetch failed",
                snapshot_path=snapshot_path,
                duration_ms=duration_ms,
                created_at=now,
            )
        )
        db.add(
            PriceHistory(
                product_listing_id=listing.id,
                price=None,
                currency=listing.currency,
                in_stock=listing.in_stock,
                recorded_at=now,
                status="error",
            )
        )
        db.flush()
        return ScrapeOutcome(
            status="failed",
            drift_result=None,
            snapshot_path=snapshot_path,
            should_notify_users=False,
        )

    drift = check_plausibility(
        scraped,
        previous_title=listing.raw_title,
        previous_price=listing.current_price,
    )

    if not drift.is_valid:
        reason_summary = "; ".join(drift.reasons)
        snapshot_path = (
            save_failure_snapshot(
                listing.store,
                raw_html,
                reason=drift.reasons[0] if drift.reasons else "suspect",
                snapshots_dir=snapshots_dir,
            )
            if raw_html
            else None
        )
        cfg.adapter_status = "suspect"
        db.add(
            AdapterRunLog(
                store=listing.store,
                status="suspect",
                error_message=reason_summary,
                snapshot_path=snapshot_path,
                duration_ms=duration_ms,
                created_at=now,
            )
        )
        db.add(
            PriceHistory(
                product_listing_id=listing.id,
                price=scraped.current_price,
                currency=scraped.currency or listing.currency,
                in_stock=bool(scraped.in_stock)
                if scraped.in_stock is not None
                else listing.in_stock,
                recorded_at=now,
                status="suspect",
            )
        )
        db.flush()
        return ScrapeOutcome(
            status="suspect",
            drift_result=drift,
            snapshot_path=snapshot_path,
            should_notify_users=False,
        )

    # Valid reading: update listing with fresh verified values
    listing.current_price = scraped.current_price
    listing.original_price = scraped.original_price
    if scraped.title:
        listing.raw_title = scraped.title
    if scraped.image_url:
        listing.image_url = scraped.image_url
    if scraped.in_stock is not None:
        listing.in_stock = scraped.in_stock
    listing.currency = scraped.currency
    listing.last_checked_at = now

    cfg.adapter_status = "healthy"
    db.add(
        AdapterRunLog(
            store=listing.store,
            status="success",
            error_message=None,
            snapshot_path=None,
            duration_ms=duration_ms,
            created_at=now,
        )
    )
    db.add(
        PriceHistory(
            product_listing_id=listing.id,
            price=scraped.current_price,
            currency=scraped.currency,
            in_stock=listing.in_stock,
            recorded_at=now,
            status="valid",
        )
    )
    db.flush()
    return ScrapeOutcome(
        status="valid",
        drift_result=drift,
        snapshot_path=None,
        should_notify_users=True,
    )
