from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    CanonicalProduct,
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


def build_sparkline(prices: list[Decimal], width: int = 72, height: int = 28) -> SparklineVM:
    """Normalize historical prices into an SVG polyline inside a 72x28 box."""
    if not prices:
        return SparklineVM(points="2,14 70,14", last_x=70.0, last_y=14.0)
    if len(prices) == 1:
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
            # Higher price near top (small y), lower price near bottom (larger y)
            ratio = (max_p - val) / span
            y = y_pad + ratio * usable_h
        coords.append((round(x, 1), round(y, 1)))

    points_str = " ".join(f"{x:g},{y:g}" for x, y in coords)
    last_x, last_y = coords[-1]
    return SparklineVM(points=points_str, last_x=last_x, last_y=last_y)


def _compute_discount(current_price: Decimal | None, original_price: Decimal | None) -> tuple[int, Decimal | None]:
    if current_price is None or original_price is None or original_price <= current_price or original_price <= 0:
        return 0, None
    savings = (original_price - current_price).quantize(Decimal("0.01"))
    pct = int(round(((original_price - current_price) / original_price) * 100))
    return pct, savings


def get_watchlist_dashboard_data(
    db: Session,
    user_id: int,
    q: str = "",
    store: str = "all",
    sort: str = "lowest_price",
) -> dict[str, object]:
    """Load DB-backed watchlist cards, store filter counts, ticker items, and CB alerts."""
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
            select(ProductListing.store, func.count(ProductListing.id)).group_by(ProductListing.store)
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

    stmt = (
        select(WatchlistItem)
        .where(WatchlistItem.user_id == user_id)
        .options(
            selectinload(WatchlistItem.canonical_product)
            .selectinload(CanonicalProduct.listings)
            .selectinload(ProductListing.price_history)
        )
    )
    watchlist_items = db.scalars(stmt).all()

    normalized_query = q.strip().lower()
    normalized_store = store.strip().lower() if store else "all"
    if normalized_store not in ("all", *STORE_META.keys()):
        normalized_store = "all"

    cards: list[WatchlistCardVM] = []
    total_count = len(watchlist_items)

    for item in watchlist_items:
        product = item.canonical_product
        active_listings = [lst for lst in product.listings if lst.is_active]

        if normalized_query:
            haystack = f"{product.name} {product.brand} {product.sku}".lower()
            if normalized_query not in haystack:
                continue

        if normalized_store != "all" and not any(lst.store == normalized_store for lst in active_listings):
            continue

        priced_in_stock = [lst for lst in active_listings if lst.in_stock and lst.current_price is not None]
        priced_any = [lst for lst in active_listings if lst.current_price is not None]
        best_listing: ProductListing | None = None
        if priced_in_stock:
            best_listing = min(priced_in_stock, key=lambda lst: lst.current_price)  # type: ignore[arg-type]
        elif priced_any:
            best_listing = min(priced_any, key=lambda lst: lst.current_price)  # type: ignore[arg-type]

        best_price = best_listing.current_price if best_listing else None
        best_store = best_listing.store if best_listing else None
        best_meta = STORE_META.get(best_store or "", {"code": "jd", "label": "MAGAZIN"})

        discount_pct, savings = _compute_discount(
            best_listing.current_price if best_listing else None,
            best_listing.original_price if best_listing else None,
        )

        history_prices: list[Decimal] = []
        if best_listing:
            valid_history = sorted(
                (h for h in best_listing.price_history if h.status == "valid" and h.price is not None),
                key=lambda h: h.recorded_at,
            )
            history_prices = [h.price for h in valid_history if h.price is not None][-7:]

        listing_rows: list[ListingRowVM] = []
        sorted_listings = sorted(
            active_listings,
            key=lambda lst: (
                0 if lst.in_stock else 1,
                float(lst.current_price) if lst.current_price is not None else float("inf"),
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
                    is_lowest=bool(best_listing and lst.id == best_listing.id),
                )
            )

        cards.append(
            WatchlistCardVM(
                product_id=product.id,
                name=product.name,
                brand=product.brand.upper(),
                sku=product.sku,
                image_url=product.image_url,
                in_stock=any(lst.in_stock for lst in active_listings),
                best_price=best_price,
                best_store=best_store,
                best_store_code=best_meta["code"],
                best_store_label=best_meta["label"],
                discount_percent=discount_pct,
                savings_ron=savings,
                sparkline=build_sparkline(history_prices),
                listings=listing_rows,
                created_at_ts=item.created_at.timestamp(),
            )
        )

    if sort == "biggest_discount":
        cards.sort(key=lambda c: (-c.discount_percent, float(c.best_price or 0)))
    elif sort == "recent":
        cards.sort(key=lambda c: -c.created_at_ts)
    else:
        sort = "lowest_price"
        cards.sort(key=lambda c: float(c.best_price) if c.best_price is not None else float("inf"))

    return {
        "cards": cards,
        "total_count": total_count,
        "filtered_count": len(cards),
        "q": q,
        "store": normalized_store,
        "sort": sort,
        "ticker_items": ticker_items,
        "circuit_breakers": circuit_breakers,
    }
