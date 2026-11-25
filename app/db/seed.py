import time
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import utcnow
from app.db.models import (
    AdapterRunLog,
    CanonicalProduct,
    PriceHistory,
    ProductListing,
    SiteConfig,
    User,
    WatchlistItem,
)
from app.db.session import SessionLocal, init_db

# Representative sneaker catalog matching DS-02 mock SKUs across the 3 approved Romanian
# retailers (jdsports.ro, sizeer.ro, buzzsneakers.ro). Canonical image URLs use verified
# HTTPS product photographs; UI views fall back to an offline SVG placeholder if unreachable.
SEED_PRODUCTS = [
    {
        "name": "Nike Air Jordan 1 Low 'University Blue'",
        "brand": "Nike",
        "sku": "553558-403",
        "image_url": "https://images.stockx.com/images/Air-Jordan-1-Low-University-Blue-Black-Product.jpg?fit=fill&bg=FFFFFF&w=700&h=500&fm=webp&auto=compress&q=90&trim=color",
        "target_price": Decimal("470.00"),
        "listings": [
            {
                "store": "jdsports",
                "url": "https://www.jdsports.ro/nike-air-jordan-1-low-university-blue-553558-403",
                "raw_title": "Nike Air Jordan 1 Low 'University Blue' Bărbați",
                "image_url": "https://www.jdsports.ro/media/catalog/product/cache/nike-air-jordan-1-low-university-blue-553558-403.jpg",
                "current_price": Decimal("489.99"),
                "original_price": Decimal("599.99"),
                "in_stock": True,
                "history": [
                    Decimal("599.99"),
                    Decimal("579.99"),
                    Decimal("549.99"),
                    Decimal("529.99"),
                    Decimal("489.99"),
                ],
            },
            {
                "store": "sizeer",
                "url": "https://sizeer.ro/nike-air-jordan-1-low-553558-403",
                "raw_title": "Jordan Air 1 Low University Blue 553558-403",
                "image_url": "https://sizeer.ro/media/catalog/product/cache/nike-air-jordan-1-low-553558-403.jpg",
                "current_price": Decimal("529.99"),
                "original_price": Decimal("599.99"),
                "in_stock": True,
                "history": [
                    Decimal("599.99"),
                    Decimal("589.99"),
                    Decimal("569.99"),
                    Decimal("549.99"),
                    Decimal("529.99"),
                ],
            },
            {
                "store": "buzzsneakers",
                "url": "https://www.buzzsneakers.ro/pantofi-sport/nike-air-jordan-1-low-553558-403",
                "raw_title": "Nike Pantofi sport Air Jordan 1 Low 553558-403",
                "image_url": "https://www.buzzsneakers.ro/files/thumbs/files/images/slike_proizvoda/media/553/553558-403/553558-403.jpg",
                "current_price": Decimal("519.99"),
                "original_price": Decimal("599.99"),
                "in_stock": True,
                "history": [
                    Decimal("599.99"),
                    Decimal("579.99"),
                    Decimal("559.99"),
                    Decimal("539.99"),
                    Decimal("519.99"),
                ],
            },
        ],
    },
    {
        "name": "Adidas Originals Campus 00s Core Black",
        "brand": "Adidas",
        "sku": "HQ8708",
        "image_url": "https://images.stockx.com/images/adidas-Campus-00s-Core-Black-Product.jpg?fit=fill&bg=FFFFFF&w=700&h=500&fm=webp&auto=compress&q=90&trim=color",
        "target_price": Decimal("430.00"),
        "listings": [
            {
                "store": "buzzsneakers",
                "url": "https://www.buzzsneakers.ro/pantofi-sport/adidas-originals-campus-00s-hq8708",
                "raw_title": "adidas Pantofi sport Campus 00s HQ8708",
                "image_url": "https://www.buzzsneakers.ro/files/thumbs/files/images/slike_proizvoda/media/HQ8/HQ8708/HQ8708.jpg",
                "current_price": Decimal("449.90"),
                "original_price": Decimal("549.90"),
                "in_stock": True,
                "history": [
                    Decimal("549.90"),
                    Decimal("529.90"),
                    Decimal("499.90"),
                    Decimal("479.90"),
                    Decimal("449.90"),
                ],
            },
            {
                "store": "sizeer",
                "url": "https://sizeer.ro/adidas-originals-campus-00s-hq8708",
                "raw_title": "adidas Campus 00s Core Black HQ8708",
                "image_url": "https://sizeer.ro/media/catalog/product/cache/adidas-campus-00s-hq8708.jpg",
                "current_price": Decimal("479.99"),
                "original_price": Decimal("549.99"),
                "in_stock": True,
                "history": [
                    Decimal("549.99"),
                    Decimal("539.99"),
                    Decimal("519.99"),
                    Decimal("499.99"),
                    Decimal("479.99"),
                ],
            },
            {
                "store": "jdsports",
                "url": "https://www.jdsports.ro/adidas-originals-campus-00s-hq8708",
                "raw_title": "adidas Originals Campus 00s HQ8708",
                "image_url": "https://www.jdsports.ro/media/catalog/product/cache/adidas-campus-00s-hq8708.jpg",
                "current_price": Decimal("499.99"),
                "original_price": Decimal("549.99"),
                "in_stock": True,
                "history": [
                    Decimal("549.99"),
                    Decimal("549.99"),
                    Decimal("529.99"),
                    Decimal("519.99"),
                    Decimal("499.99"),
                ],
            },
        ],
    },
    {
        "name": "Nike Air Jordan 1 Retro High OG 'Lost & Found'",
        "brand": "Nike",
        "sku": "DZ5485-612",
        "image_url": "https://images.stockx.com/images/Air-Jordan-1-Retro-High-OG-Chicago-Reimagined-Product.jpg?fit=fill&bg=FFFFFF&w=700&h=500&fm=webp&auto=compress&q=90&trim=color",
        "target_price": Decimal("850.00"),
        "listings": [
            {
                "store": "sizeer",
                "url": "https://sizeer.ro/nike-air-jordan-1-retro-high-og-dz5485-612",
                "raw_title": "Jordan Air 1 Retro High OG Chicago Lost & Found DZ5485-612",
                "image_url": "https://sizeer.ro/media/catalog/product/cache/nike-jordan-1-high-dz5485-612.jpg",
                "current_price": Decimal("899.99"),
                "original_price": Decimal("999.99"),
                "in_stock": True,
                "history": [
                    Decimal("999.99"),
                    Decimal("979.99"),
                    Decimal("949.99"),
                    Decimal("919.99"),
                    Decimal("899.99"),
                ],
            },
            {
                "store": "jdsports",
                "url": "https://www.jdsports.ro/nike-air-jordan-1-retro-high-og-dz5485-612",
                "raw_title": "Nike Air Jordan 1 High OG Lost & Found DZ5485-612",
                "image_url": "https://www.jdsports.ro/media/catalog/product/cache/nike-jordan-1-high-dz5485-612.jpg",
                "current_price": Decimal("949.99"),
                "original_price": Decimal("999.99"),
                "in_stock": False,
                "history": [
                    Decimal("999.99"),
                    Decimal("999.99"),
                    Decimal("969.99"),
                    Decimal("949.99"),
                    Decimal("949.99"),
                ],
            },
            {
                "store": "buzzsneakers",
                "url": "https://www.buzzsneakers.ro/pantofi-sport/nike-air-jordan-1-high-og-dz5485-612",
                "raw_title": "Nike Pantofi sport Air Jordan 1 Retro High OG DZ5485-612",
                "image_url": "https://www.buzzsneakers.ro/files/thumbs/files/images/slike_proizvoda/media/DZ5/DZ5485-612/DZ5485-612.jpg",
                "current_price": Decimal("929.99"),
                "original_price": Decimal("999.99"),
                "in_stock": True,
                "history": [
                    Decimal("999.99"),
                    Decimal("989.99"),
                    Decimal("959.99"),
                    Decimal("939.99"),
                    Decimal("929.99"),
                ],
            },
        ],
    },
]


def seed_site_configs(session: Session) -> None:
    """Create default polite-polling SiteConfig rows for each supported store."""
    for store in settings.SUPPORTED_STORES:
        existing = session.scalar(select(SiteConfig).where(SiteConfig.store == store))
        if not existing:
            session.add(
                SiteConfig(
                    store=store,
                    polling_interval_minutes=settings.DEFAULT_POLLING_INTERVAL_MINUTES,
                    min_delay_seconds=settings.DEFAULT_MIN_DELAY_SECONDS,
                    max_requests_per_hour=settings.DEFAULT_MAX_REQUESTS_PER_HOUR,
                    circuit_breaker_open=False,
                )
            )
    session.flush()


def seed_users(session: Session) -> dict[str, User]:
    """Ensure demo admin and regular user accounts exist."""
    env = settings.ENVIRONMENT.strip().lower()
    weak_passwords = {"Admin123!", "User123!", "change-me-admin-password", "change-me-user-password"}
    accounts = [
        (settings.SEED_ADMIN_EMAIL.strip().lower(), settings.SEED_ADMIN_PASSWORD, "admin"),
        (settings.SEED_USER_EMAIL.strip().lower(), settings.SEED_USER_PASSWORD, "user"),
    ]
    if env in {"production", "prod", "staging"}:
        for _, password, role in accounts:
            if password in weak_passwords or len(password) < 12:
                raise ValueError(
                    f"Default or weak SEED password for {role} is forbidden in {env}"
                )
    users_by_email: dict[str, User] = {}
    for email, password, role in accounts:
        user = session.scalar(select(User).where(User.email == email))
        if not user:
            user = User(
                email=email,
                password_hash=hash_password(password),
                role=role,
            )
            session.add(user)
            session.flush()
        users_by_email[email] = user
    return users_by_email


def seed_products_and_listings(session: Session) -> list[CanonicalProduct]:
    """Create canonical sneaker products, store listings, and initial price history."""
    now = utcnow()
    canonical_products: list[CanonicalProduct] = []

    for prod_spec in SEED_PRODUCTS:
        product = session.scalar(
            select(CanonicalProduct).where(CanonicalProduct.sku == prod_spec["sku"])
        )
        if not product:
            product = CanonicalProduct(
                name=prod_spec["name"],
                brand=prod_spec["brand"],
                sku=prod_spec["sku"],
                image_url=prod_spec["image_url"],
            )
            session.add(product)
            session.flush()
        elif product.image_url != prod_spec["image_url"]:
            product.image_url = prod_spec["image_url"]
        canonical_products.append(product)

        for listing_spec in prod_spec["listings"]:
            listing = session.scalar(
                select(ProductListing).where(
                    ProductListing.canonical_product_id == product.id,
                    ProductListing.store == listing_spec["store"],
                )
            )
            if not listing:
                listing = ProductListing(
                    canonical_product_id=product.id,
                    store=listing_spec["store"],
                    url=listing_spec["url"],
                    raw_title=listing_spec["raw_title"],
                    image_url=listing_spec["image_url"],
                    current_price=listing_spec["current_price"],
                    original_price=listing_spec["original_price"],
                    currency="RON",
                    in_stock=listing_spec["in_stock"],
                    last_checked_at=now,
                    is_active=True,
                )
                session.add(listing)
                session.flush()

            has_history = session.scalar(
                select(PriceHistory.id).where(
                    PriceHistory.product_listing_id == listing.id
                )
            )
            if not has_history:
                points = listing_spec["history"]
                for idx, price in enumerate(points):
                    days_ago = (len(points) - 1 - idx) * 3
                    session.add(
                        PriceHistory(
                            product_listing_id=listing.id,
                            price=price,
                            currency="RON",
                            in_stock=listing_spec["in_stock"] if idx == len(points) - 1 else True,
                            recorded_at=now - timedelta(days=days_ago),
                            status="valid",
                        )
                    )
    session.flush()
    return canonical_products


def seed_watchlist_items(
    session: Session, demo_user: User, products: list[CanonicalProduct]
) -> None:
    """Attach demo products to the demo user's watchlist idempotently."""
    targets_by_sku = {spec["sku"]: spec["target_price"] for spec in SEED_PRODUCTS}
    for product in products:
        existing = session.scalar(
            select(WatchlistItem).where(
                WatchlistItem.user_id == demo_user.id,
                WatchlistItem.canonical_product_id == product.id,
            )
        )
        if not existing:
            session.add(
                WatchlistItem(
                    user_id=demo_user.id,
                    canonical_product_id=product.id,
                    target_price=targets_by_sku.get(product.sku),
                    min_discount_percent=Decimal("15.00"),
                    notify_stock=True,
                    notify_email=True,
                    notify_telegram=False,
                )
            )
    session.flush()


def seed_adapter_run_logs(session: Session) -> None:
    """Ensure each supported store has an initial adapter run log entry."""
    now = utcnow()
    for idx, store in enumerate(settings.SUPPORTED_STORES):
        has_log = session.scalar(
            select(AdapterRunLog.id).where(AdapterRunLog.store == store)
        )
        if not has_log:
            session.add(
                AdapterRunLog(
                    store=store,
                    status="success",
                    error_message=None,
                    snapshot_path=None,
                    duration_ms=320 + idx * 45,
                    created_at=now - timedelta(hours=1),
                )
            )
    session.flush()


def seed_all(session: Session) -> None:
    """Run all idempotent database seeders inside a rollback-safe transaction."""
    try:
        bind = session.get_bind()
        if bind is not None and bind.dialect.name == "postgresql":
            session.execute(text("SELECT pg_advisory_xact_lock(23002)"))
        seed_site_configs(session)
        users = seed_users(session)
        products = seed_products_and_listings(session)
        seed_watchlist_items(session, users[settings.SEED_USER_EMAIL.strip().lower()], products)
        seed_adapter_run_logs(session)
        session.commit()
    except Exception:
        session.rollback()
        raise


def main(max_attempts: int = 10, retry_delay_seconds: float = 2.0) -> None:
    """Initialize schema and seed the configured database with startup DB retry."""
    last_error: OperationalError | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            init_db()
            with SessionLocal() as session:
                seed_all(session)
            return
        except OperationalError as exc:
            last_error = exc
            if attempt == max_attempts:
                break
            time.sleep(retry_delay_seconds)
    assert last_error is not None
    raise last_error


if __name__ == "__main__":
    main()
