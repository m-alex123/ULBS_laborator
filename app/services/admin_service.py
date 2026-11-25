"""Admin operations service for DS-05 adapter health, snapshots, and SKU deduplication."""

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import PROJECT_ROOT, settings
from app.db.models import (
    AdapterRunLog,
    CanonicalProduct,
    ProductListing,
    SiteConfig,
    WatchlistItem,
)
from app.services.watchlist_service import STORE_META


@dataclass(slots=True)
class StoreHealthVM:
    store: str
    store_code: str
    store_label: str
    domain: str
    adapter_status: str
    circuit_breaker_open: bool
    polling_interval_minutes: int
    min_delay_seconds: int
    max_requests_per_hour: int
    consecutive_failures: int
    last_run: AdapterRunLog | None
    listing_count: int


def _count_consecutive_failures(logs: list[AdapterRunLog]) -> int:
    count = 0
    for log in logs:
        if log.status == "success":
            break
        count += 1
    return count


def _resolve_safe_snapshot_file(snapshot_path: str | None) -> Path | None:
    """Resolve snapshot_path strictly inside settings.SNAPSHOTS_DIR to prevent traversal."""
    if not snapshot_path:
        return None
    snapshots_root = settings.SNAPSHOTS_DIR.resolve()
    raw = Path(snapshot_path)
    candidates = [raw] if raw.is_absolute() else [PROJECT_ROOT / raw, snapshots_root / raw.name]
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved.is_relative_to(snapshots_root) and resolved.is_file():
            return resolved
    return None


def read_safe_snapshot(db: Session, log_id: int) -> tuple[AdapterRunLog, str] | None:
    """Return (AdapterRunLog, html_text) for an existing snapshot inside SNAPSHOTS_DIR."""
    log = db.get(AdapterRunLog, log_id)
    if log is None:
        return None
    resolved = _resolve_safe_snapshot_file(log.snapshot_path)
    if resolved is None:
        return None
    return log, resolved.read_text(encoding="utf-8", errors="replace")


def get_admin_dashboard_data(
    db: Session,
    *,
    snapshot_id: int | None = None,
) -> dict[str, object]:
    """Assemble DS-05 adapter health cards, run logs, snapshot preview, and SKU reviews."""
    configs_by_store = {
        cfg.store: cfg for cfg in db.scalars(select(SiteConfig).order_by(SiteConfig.id)).all()
    }
    listing_counts = dict(
        db.execute(
            select(ProductListing.store, func.count(ProductListing.id))
            .where(ProductListing.is_active.is_(True))
            .group_by(ProductListing.store)
        ).all()
    )

    recent_logs = list(
        db.scalars(
            select(AdapterRunLog)
            .order_by(AdapterRunLog.created_at.desc(), AdapterRunLog.id.desc())
            .limit(30)
        ).all()
    )

    logs_by_store: dict[str, list[AdapterRunLog]] = {}
    for log in recent_logs:
        logs_by_store.setdefault(log.store, []).append(log)

    store_cards: list[StoreHealthVM] = []
    for store_key, meta in STORE_META.items():
        cfg = configs_by_store.get(store_key)
        store_logs = logs_by_store.get(store_key, [])
        store_cards.append(
            StoreHealthVM(
                store=store_key,
                store_code=meta["code"],
                store_label=meta["label"],
                domain=meta["domain"],
                adapter_status=cfg.adapter_status if cfg else "healthy",
                circuit_breaker_open=cfg.circuit_breaker_open if cfg else False,
                polling_interval_minutes=cfg.polling_interval_minutes
                if cfg
                else settings.DEFAULT_POLLING_INTERVAL_MINUTES,
                min_delay_seconds=cfg.min_delay_seconds
                if cfg
                else settings.DEFAULT_MIN_DELAY_SECONDS,
                max_requests_per_hour=cfg.max_requests_per_hour
                if cfg
                else settings.DEFAULT_MAX_REQUESTS_PER_HOUR,
                consecutive_failures=_count_consecutive_failures(store_logs),
                last_run=store_logs[0] if store_logs else None,
                listing_count=listing_counts.get(store_key, 0),
            )
        )

    uncertain_listings = list(
        db.scalars(
            select(ProductListing)
            .where(ProductListing.match_needs_review.is_(True))
            .options(joinedload(ProductListing.canonical_product))
            .order_by(ProductListing.id.desc())
        ).all()
    )

    suggested_ids = {
        lst.suggested_canonical_product_id
        for lst in uncertain_listings
        if lst.suggested_canonical_product_id is not None
    }
    suggested_map: dict[int, CanonicalProduct] = {}
    if suggested_ids:
        for prod in db.scalars(
            select(CanonicalProduct).where(CanonicalProduct.id.in_(suggested_ids))
        ).all():
            suggested_map[prod.id] = prod

    review_rows = [
        {
            "listing": lst,
            "store_code": STORE_META.get(lst.store, {}).get("code", "jd"),
            "store_label": STORE_META.get(lst.store, {}).get("label", lst.store.upper()),
            "current_canonical": lst.canonical_product,
            "suggested_canonical": suggested_map.get(lst.suggested_canonical_product_id)
            if lst.suggested_canonical_product_id is not None
            else None,
        }
        for lst in uncertain_listings
    ]

    snapshot_preview: dict[str, object] | None = None
    if snapshot_id is not None:
        loaded = read_safe_snapshot(db, snapshot_id)
        if loaded is not None:
            snap_log, content = loaded
            snapshot_preview = {
                "log": snap_log,
                "content": content,
            }

    return {
        "store_cards": store_cards,
        "recent_logs": recent_logs,
        "review_rows": review_rows,
        "snapshot_preview": snapshot_preview,
    }


def reset_store_adapter(db: Session, store: str) -> bool:
    """Acknowledge suspect/circuit-open state and restore store adapter to healthy."""
    if store not in STORE_META:
        return False
    cfg = db.scalar(select(SiteConfig).where(SiteConfig.store == store))
    if cfg is None:
        cfg = SiteConfig(store=store)
        db.add(cfg)
    cfg.adapter_status = "healthy"
    cfg.circuit_breaker_open = False
    db.add(
        AdapterRunLog(
            store=store,
            status="success",
            error_message="Resetat și confirmat de administrator.",
            snapshot_path=None,
            duration_ms=0,
        )
    )
    db.commit()
    return True


def confirm_deduplication_match(db: Session, listing_id: int) -> tuple[bool, str]:
    """Merge an uncertain listing onto its suggested CanonicalProduct when safe."""
    listing = db.get(ProductListing, listing_id)
    if listing is None:
        return False, "Listarea nu a fost găsită."

    target_id = listing.suggested_canonical_product_id
    if target_id is None:
        listing.match_needs_review = False
        db.commit()
        return True, "Potrivirea a fost confirmată."

    target = db.get(CanonicalProduct, target_id)
    if target is None:
        listing.match_needs_review = False
        listing.suggested_canonical_product_id = None
        db.commit()
        return False, "Produsul canonic țintă nu mai există; marcajul a fost eliminat."

    conflict = db.scalar(
        select(ProductListing.id).where(
            ProductListing.canonical_product_id == target.id,
            ProductListing.store == listing.store,
            ProductListing.id != listing.id,
        )
    )
    if conflict is not None:
        return (
            False,
            f"Produsul țintă (SKU {target.sku}) are deja o listare pentru {listing.store}.",
        )

    old_canonical_id = listing.canonical_product_id
    listing.canonical_product_id = target.id
    listing.match_needs_review = False
    listing.suggested_canonical_product_id = None
    db.flush()

    if old_canonical_id != target.id:
        old_watchlist_items = db.scalars(
            select(WatchlistItem).where(WatchlistItem.canonical_product_id == old_canonical_id)
        ).all()
        for wl in old_watchlist_items:
            existing_target_wl = db.scalar(
                select(WatchlistItem.id).where(
                    WatchlistItem.user_id == wl.user_id,
                    WatchlistItem.canonical_product_id == target.id,
                )
            )
            if existing_target_wl is not None:
                db.delete(wl)
            else:
                wl.canonical_product_id = target.id
        db.flush()

        remaining = db.scalar(
            select(ProductListing.id).where(
                ProductListing.canonical_product_id == old_canonical_id
            )
        )
        if remaining is None:
            old_canonical = db.get(CanonicalProduct, old_canonical_id)
            if old_canonical is not None:
                db.delete(old_canonical)

    db.commit()
    return True, f"Listarea a fost comasată în produsul SKU {target.sku}."


def reject_deduplication_match(db: Session, listing_id: int) -> bool:
    """Reject a suggested match so the listing remains a separate CanonicalProduct."""
    listing = db.get(ProductListing, listing_id)
    if listing is None:
        return False
    listing.match_needs_review = False
    listing.suggested_canonical_product_id = None
    db.commit()
    return True
