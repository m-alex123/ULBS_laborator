from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    CanonicalProduct,
    PriceHistory,
    ProductListing,
    SiteConfig,
    WatchlistItem,
)

STORE_META: dict[str, dict[str, str]] = {
    "jdsports": {"code": "jd", "label": "JD SPORTS", "domain": "jdsports.ro"},
    "sizeer": {"code": "sizeer", "label": "SIZEER", "domain": "sizeer.ro"},
    "buzzsneakers": {"code": "buzz", "label": "BUZZ SNEAKERS", "domain": "buzzsneakers.ro"},
}


@dataclass(slots=True)
class ListingRowVM:
    store: str
    store_code: str
    store_label: str
    url: str
    current_price: Decimal | None
    original_price: Decimal | None
    in_stock: bool
    is_lowest: bool


@dataclass(slots=True)
class SparklineVM:
    points: str
    last_x: float
    last_y: float


@dataclass(slots=True)
class WatchlistCardVM:
    product_id: int
    name: str
    brand: str
    sku: str
    image_url: str | None
    photo_source_label: str
    in_stock: bool
    best_price: Decimal | None
    best_store: str | None
    best_store_code: str
    best_store_label: str
    discount_percent: int
    savings_ron: Decimal | None
    sparkline: SparklineVM
    listings: list[ListingRowVM]
    created_at_ts: float
    in_watchlist: bool = False


def _safe_image_url(url: str | None) -> str | None:
    """Allow only HTTPS external image URLs or local /static/ assets."""
    if not url:
        return None
    cleaned = url.strip()
    if cleaned.startswith("https://") or cleaned.startswith("/static/"):
        return cleaned
    return None


def _derive_photo_source_label(image_url: str | None) -> str:
    """Derive accurate source attribution label from validated image URL."""
    if not image_url:
        return "MOD OFFLINE"
    host = urlparse(image_url).netloc.lower()
    if "stockx.com" in host:
        return "FOTO: STOCKX"
    if "jdsports" in host:
        return "FOTO: JD SPORTS"
    if "sizeer" in host:
        return "FOTO: SIZEER"
    if "buzzsneakers" in host:
        return "FOTO: BUZZ"
    return "FOTO: PRODUS"


def build_sparkline(prices: list[Decimal], width: int = 72, height: int = 28) -> SparklineVM:
    """Normalize historical prices into an SVG polyline inside a 72x28 box."""
    if len(prices) <= 1:
        return SparklineVM(points="2,14 70,14", last_x=70.0, last_y=14.0)

    nums = [float(p) for p in prices]
    min_p = min(nums)
    max_p = max(nums)
    span = max_p - min_p
    x_pad = 2.0
    y_pad = 4.0
    usable_w = width - 2 * x_pad
    usable_h = height - 2 * y_pad

    coords: list[tuple[float, float]] = []
    for idx, val in enumerate(nums):
        x = x_pad + (idx / (len(nums) - 1)) * usable_w
        if span == 0:
            y = height / 2.0
        else:
            ratio = (max_p - val) / span
            y = y_pad + ratio * usable_h
        coords.append((round(x, 1), round(y, 1)))

    points_str = " ".join(f"{x:g},{y:g}" for x, y in coords)
    last_x, last_y = coords[-1]
    return SparklineVM(points=points_str, last_x=last_x, last_y=last_y)


def _compute_discount(
    current_price: Decimal | None,
    original_price: Decimal | None,
) -> tuple[int, Decimal | None]:
    if (
        current_price is None
        or original_price is None
        or current_price <= 0
        or original_price <= current_price
    ):
        return 0, None
    savings = (original_price - current_price).quantize(Decimal("0.01"))
    pct = int(round(((original_price - current_price) / original_price) * 100))
    return pct, savings


def _get_site_strip_data(db: Session) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    """Load retailer ticker metrics and open circuit breaker notices."""
    site_configs = db.scalars(select(SiteConfig).order_by(SiteConfig.id)).all()
    circuit_breakers = [
        {
            "store": cfg.store,
            "domain": STORE_META.get(cfg.store, {}).get("domain", cfg.store),
            "label": STORE_META.get(cfg.store, {}).get("label", cfg.store.upper()),
        }
        for cfg in site_configs
        if cfg.circuit_breaker_open
    ]

    listing_counts = dict(
        db.execute(
            select(ProductListing.store, func.count(ProductListing.id))
            .where(ProductListing.is_active.is_(True))
            .group_by(ProductListing.store)
        ).all()
    )
    ticker_items = []
    for cfg in site_configs:
        meta = STORE_META.get(cfg.store, {"code": "jd", "label": cfg.store.upper(), "domain": cfg.store})
        ticker_items.append(
            {
                "store": cfg.store,
                "code": meta["code"],
                "label": meta["label"],
                "domain": meta["domain"],
                "count": listing_counts.get(cfg.store, 0),
                "min_delay": cfg.min_delay_seconds,
                "circuit_breaker_open": cfg.circuit_breaker_open,
            }
        )
    return ticker_items, circuit_breakers


def _pick_best_listing(active_listings: list[ProductListing]) -> ProductListing | None:
    priced_in_stock = [
        lst for lst in active_listings
        if lst.in_stock and lst.current_price is not None and lst.current_price > 0
    ]
    if priced_in_stock:
        return min(
            priced_in_stock,
            key=lambda lst: (lst.current_price, lst.store),  # type: ignore[arg-type]
        )
    priced_any = [
        lst for lst in active_listings
        if lst.current_price is not None and lst.current_price > 0
    ]
    if priced_any:
        return min(
            priced_any,
            key=lambda lst: (lst.current_price, lst.store),  # type: ignore[arg-type]
        )
    return None


def _build_cards_dashboard_payload(
    db: Session,
    product_entries: list[tuple[CanonicalProduct, float, bool]],
    *,
    q: str = "",
    store: str = "all",
    sort: str = "lowest_price",
) -> dict[str, object]:
    """Shared card filtering, sorting, sparkline query, and ticker assembly for DS-02/Catalog."""
    ticker_items, circuit_breakers = _get_site_strip_data(db)

    normalized_query = q.strip().lower()
    normalized_store = store.strip().lower() if store else "all"
    if normalized_store not in ("all", *STORE_META.keys()):
        normalized_store = "all"

    normalized_sort = (sort or "lowest_price").strip().lower()
    if normalized_sort not in ("lowest_price", "biggest_discount", "recent"):
        normalized_sort = "lowest_price"

    total_count = len(product_entries)

    selected_entries: list[tuple[CanonicalProduct, float, bool, list[ProductListing], ProductListing | None]] = []
    best_listing_ids: list[int] = []

    for product, sort_ts, in_watchlist in product_entries:
        active_listings = [lst for lst in product.listings if lst.is_active]

        if normalized_query:
            haystack = f"{product.name} {product.brand} {product.sku}".lower()
            if normalized_query not in haystack:
                continue

        if normalized_store != "all" and not any(lst.store == normalized_store for lst in active_listings):
            continue

        best_listing = _pick_best_listing(active_listings)
        if best_listing is not None:
            best_listing_ids.append(best_listing.id)
        selected_entries.append((product, sort_ts, in_watchlist, active_listings, best_listing))

    history_by_listing: dict[int, list[Decimal]] = {}
    if best_listing_ids:
        ranked_sq = (
            select(
                PriceHistory.product_listing_id.label("listing_id"),
                PriceHistory.price.label("price"),
                PriceHistory.recorded_at.label("recorded_at"),
                func.row_number()
                .over(
                    partition_by=PriceHistory.product_listing_id,
                    order_by=PriceHistory.recorded_at.desc(),
                )
                .label("rn"),
            )
            .where(
                PriceHistory.product_listing_id.in_(best_listing_ids),
                PriceHistory.status == "valid",
                PriceHistory.price.is_not(None),
            )
            .subquery()
        )
        rows = db.execute(
            select(ranked_sq.c.listing_id, ranked_sq.c.price)
            .where(ranked_sq.c.rn <= 7)
            .order_by(ranked_sq.c.listing_id, ranked_sq.c.recorded_at.asc())
        ).all()
        for listing_id, price in rows:
            history_by_listing.setdefault(listing_id, []).append(price)

    cards: list[WatchlistCardVM] = []
    for product, sort_ts, in_watchlist, active_listings, best_listing in selected_entries:
        safe_img = _safe_image_url(product.image_url)

        best_price = best_listing.current_price if best_listing else None
        best_store = best_listing.store if best_listing else None
        best_meta = STORE_META.get(best_store or "", {"code": "", "label": ""})

        discount_pct, savings = _compute_discount(
            best_listing.current_price if best_listing else None,
            best_listing.original_price if best_listing else None,
        )

        history_prices = history_by_listing.get(best_listing.id, []) if best_listing else []

        listing_rows: list[ListingRowVM] = []
        sorted_listings = sorted(
            active_listings,
            key=lambda lst: (
                0 if lst.in_stock else 1,
                float(lst.current_price)
                if lst.current_price is not None and lst.current_price > 0
                else float("inf"),
                lst.store,
            ),
        )
        for lst in sorted_listings:
            meta = STORE_META.get(lst.store, {"code": "jd", "label": lst.store.upper()})
            listing_rows.append(
                ListingRowVM(
                    store=lst.store,
                    store_code=meta["code"],
                    store_label=meta["label"],
                    url=lst.url,
                    current_price=lst.current_price,
                    original_price=lst.original_price,
                    in_stock=lst.in_stock,
                    is_lowest=bool(
                        best_listing and best_listing.in_stock and lst.id == best_listing.id
                    ),
                )
            )

        cards.append(
            WatchlistCardVM(
                product_id=product.id,
                name=product.name,
                brand=product.brand.upper(),
                sku=product.sku,
                image_url=safe_img,
                photo_source_label=_derive_photo_source_label(safe_img),
                in_stock=any(lst.in_stock for lst in active_listings),
                best_price=best_price,
                best_store=best_store,
                best_store_code=best_meta["code"],
                best_store_label=best_meta["label"],
                discount_percent=discount_pct,
                savings_ron=savings,
                sparkline=build_sparkline(history_prices),
                listings=listing_rows,
                created_at_ts=sort_ts,
                in_watchlist=in_watchlist,
            )
        )

    if normalized_sort == "biggest_discount":
        cards.sort(
            key=lambda c: (
                -c.discount_percent,
                float(c.best_price) if c.best_price is not None else float("inf"),
            )
        )
    elif normalized_sort == "recent":
        cards.sort(key=lambda c: -c.created_at_ts)
    else:
        cards.sort(key=lambda c: float(c.best_price) if c.best_price is not None else float("inf"))

    return {
        "cards": cards,
        "total_count": total_count,
        "filtered_count": len(cards),
        "q": q,
        "store": normalized_store,
        "sort": normalized_sort,
        "ticker_items": ticker_items,
        "circuit_breakers": circuit_breakers,
    }


def get_watchlist_dashboard_data(
    db: Session,
    user_id: int,
    q: str = "",
    store: str = "all",
    sort: str = "lowest_price",
) -> dict[str, object]:
    """Load DB-backed watchlist cards for an authenticated user."""
    stmt = (
        select(WatchlistItem)
        .where(WatchlistItem.user_id == user_id)
        .options(
            selectinload(WatchlistItem.canonical_product).selectinload(CanonicalProduct.listings)
        )
    )
    watchlist_items = db.scalars(stmt).all()
    entries = [
        (item.canonical_product, item.created_at.timestamp(), True)
        for item in watchlist_items
    ]
    return _build_cards_dashboard_payload(db, entries, q=q, store=store, sort=sort)


def get_public_catalog_data(
    db: Session,
    *,
    q: str = "",
    store: str = "all",
    sort: str = "lowest_price",
    user_id: int | None = None,
) -> dict[str, object]:
    """Load public read-only canonical catalog cards for Guest or authenticated browsing."""
    products = db.scalars(
        select(CanonicalProduct)
        .options(selectinload(CanonicalProduct.listings))
        .order_by(CanonicalProduct.id.asc())
    ).all()
    watched_ids: set[int] = set()
    if user_id is not None:
        watched_ids = set(
            db.scalars(
                select(WatchlistItem.canonical_product_id).where(WatchlistItem.user_id == user_id)
            ).all()
        )
    entries = [
        (prod, prod.created_at.timestamp(), prod.id in watched_ids)
        for prod in products
        if any(lst.is_active for lst in prod.listings)
    ]
    return _build_cards_dashboard_payload(db, entries, q=q, store=store, sort=sort)


def get_product_detail_data(
    db: Session,
    canonical_id: int,
    *,
    user_id: int | None = None,
) -> dict[str, object] | None:
    """Build DS-03 comparison and suspect-free chronological price history for a product."""
    product = db.scalar(
        select(CanonicalProduct)
        .where(CanonicalProduct.id == canonical_id)
        .options(selectinload(CanonicalProduct.listings))
    )
    if product is None:
        return None

    ticker_items, circuit_breakers = _get_site_strip_data(db)
    active_listings = [lst for lst in product.listings if lst.is_active]
    listings_by_store = {lst.store: lst for lst in active_listings}
    best_listing = _pick_best_listing(active_listings)

    comparison_rows: list[dict[str, object]] = []
    for store_key, meta in STORE_META.items():
        lst = listings_by_store.get(store_key)
        if lst is None:
            comparison_rows.append(
                {
                    "store": store_key,
                    "store_code": meta["code"],
                    "store_label": meta["label"],
                    "domain": meta["domain"],
                    "is_listed": False,
                    "url": None,
                    "current_price": None,
                    "original_price": None,
                    "discount_percent": 0,
                    "savings_ron": None,
                    "in_stock": False,
                    "is_lowest": False,
                    "last_checked_at": None,
                    "raw_title": None,
                }
            )
            continue

        pct, savings = _compute_discount(lst.current_price, lst.original_price)
        comparison_rows.append(
            {
                "store": store_key,
                "store_code": meta["code"],
                "store_label": meta["label"],
                "domain": meta["domain"],
                "is_listed": True,
                "url": lst.url,
                "current_price": lst.current_price,
                "original_price": lst.original_price,
                "discount_percent": pct,
                "savings_ron": savings,
                "in_stock": lst.in_stock,
                "is_lowest": bool(
                    best_listing and best_listing.in_stock and lst.id == best_listing.id
                ),
                "last_checked_at": lst.last_checked_at,
                "raw_title": lst.raw_title,
            }
        )

    listing_ids = [lst.id for lst in active_listings]
    listing_store_map = {lst.id: lst.store for lst in active_listings}

    valid_history_rows: list[PriceHistory] = []
    excluded_suspect_count = 0
    if listing_ids:
        valid_history_rows = list(
            db.scalars(
                select(PriceHistory)
                .where(
                    PriceHistory.product_listing_id.in_(listing_ids),
                    PriceHistory.status == "valid",
                    PriceHistory.price.is_not(None),
                )
                .order_by(PriceHistory.recorded_at.asc(), PriceHistory.id.asc())
            ).all()
        )
        excluded_suspect_count = int(
            db.scalar(
                select(func.count(PriceHistory.id)).where(
                    PriceHistory.product_listing_id.in_(listing_ids),
                    PriceHistory.status == "suspect",
                )
            )
            or 0
        )

    valid_prices = [row.price for row in valid_history_rows if row.price is not None]
    min_price = min(valid_prices) if valid_prices else None
    max_price = max(valid_prices) if valid_prices else None
    avg_price = (
        (sum(valid_prices) / Decimal(len(valid_prices))).quantize(Decimal("0.01"))
        if valid_prices
        else None
    )

    # Chart.js dataset grouped by store using strictly valid PriceHistory rows
    date_labels: list[str] = []
    seen_dates: set[str] = set()
    points_by_store_date: dict[str, dict[str, float]] = {k: {} for k in STORE_META}
    history_table_rows: list[dict[str, object]] = []

    for row in valid_history_rows:
        store_key = listing_store_map.get(row.product_listing_id, "jdsports")
        meta = STORE_META.get(store_key, {"code": "jd", "label": store_key.upper()})
        date_label = row.recorded_at.strftime("%Y-%m-%d %H:%M")
        if date_label not in seen_dates:
            seen_dates.add(date_label)
            date_labels.append(date_label)
        if row.price is not None:
            points_by_store_date.setdefault(store_key, {})[date_label] = float(row.price)

        history_table_rows.append(
            {
                "recorded_at": row.recorded_at,
                "store_code": meta["code"],
                "store_label": meta["label"],
                "price": row.price,
                "currency": row.currency,
                "in_stock": row.in_stock,
            }
        )

    history_table_rows.reverse()

    store_colors = {
        "jdsports": "#006340",
        "sizeer": "#B54708",
        "buzzsneakers": "#D92D20",
    }
    chart_datasets = []
    for store_key, meta in STORE_META.items():
        store_map = points_by_store_date.get(store_key, {})
        if not store_map:
            continue
        chart_datasets.append(
            {
                "label": meta["label"],
                "data": [store_map.get(lbl) for lbl in date_labels],
                "borderColor": store_colors.get(store_key, "#0D0D0D"),
                "backgroundColor": store_colors.get(store_key, "#0D0D0D"),
                "spanGaps": True,
                "tension": 0.25,
            }
        )

    watchlist_item: WatchlistItem | None = None
    if user_id is not None:
        watchlist_item = db.scalar(
            select(WatchlistItem).where(
                WatchlistItem.user_id == user_id,
                WatchlistItem.canonical_product_id == product.id,
            )
        )

    safe_img = _safe_image_url(product.image_url)
    best_discount, best_savings = _compute_discount(
        best_listing.current_price if best_listing else None,
        best_listing.original_price if best_listing else None,
    )
    best_meta = STORE_META.get(best_listing.store if best_listing else "", {"code": "", "label": ""})

    return {
        "product": product,
        "image_url": safe_img,
        "photo_source_label": _derive_photo_source_label(safe_img),
        "best_listing": best_listing,
        "best_store_code": best_meta["code"],
        "best_store_label": best_meta["label"],
        "best_discount_percent": best_discount,
        "best_savings_ron": best_savings,
        "in_stock_any": any(lst.in_stock for lst in active_listings),
        "comparison_rows": comparison_rows,
        "min_price": min_price,
        "max_price": max_price,
        "avg_price": avg_price,
        "excluded_suspect_count": excluded_suspect_count,
        "history_rows": history_table_rows,
        "sparkline": build_sparkline(valid_prices[-12:], width=240, height=56),
        "chart_payload": {"labels": date_labels, "datasets": chart_datasets},
        "watchlist_item": watchlist_item,
        "ticker_items": ticker_items,
        "circuit_breakers": circuit_breakers,
    }


def set_watchlist_target(
    db: Session,
    *,
    user_id: int,
    canonical_product_id: int,
    target_price: Decimal | None,
) -> WatchlistItem | None:
    """Create or update a user's WatchlistItem target price for a CanonicalProduct."""
    product = db.get(CanonicalProduct, canonical_product_id)
    if product is None:
        return None
    item = db.scalar(
        select(WatchlistItem).where(
            WatchlistItem.user_id == user_id,
            WatchlistItem.canonical_product_id == canonical_product_id,
        )
    )
    if item is None:
        item = WatchlistItem(
            user_id=user_id,
            canonical_product_id=canonical_product_id,
            target_price=target_price,
        )
        db.add(item)
    else:
        item.target_price = target_price
    db.commit()
    db.refresh(item)
    return item


def remove_watchlist_item(
    db: Session,
    *,
    user_id: int,
    canonical_product_id: int,
) -> bool:
    """Delete a user's WatchlistItem if present; returns True when deleted."""
    item = db.scalar(
        select(WatchlistItem).where(
            WatchlistItem.user_id == user_id,
            WatchlistItem.canonical_product_id == canonical_product_id,
        )
    )
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True
