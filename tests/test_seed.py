from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_password
from app.db.models import (
    AdapterRunLog,
    CanonicalProduct,
    PriceHistory,
    ProductListing,
    SiteConfig,
    User,
    WatchlistItem,
)
from app.db.seed import seed_all


def test_seed_all_populates_accounts_stores_products_and_images(db_session: Session) -> None:
    seed_all(db_session)

    admin = db_session.query(User).filter_by(email=settings.SEED_ADMIN_EMAIL).one_or_none()
    demo_user = db_session.query(User).filter_by(email=settings.SEED_USER_EMAIL).one_or_none()
    assert admin is not None and admin.role == "admin"
    assert demo_user is not None and demo_user.role == "user"

    stores = {cfg.store for cfg in db_session.query(SiteConfig).all()}
    assert stores == {"jdsports", "sizeer", "buzzsneakers"}

    products = db_session.query(CanonicalProduct).all()
    listings = db_session.query(ProductListing).all()
    history_rows = db_session.query(PriceHistory).all()
    watchlist_rows = db_session.query(WatchlistItem).filter_by(user_id=demo_user.id).all()

    assert len(products) >= 3
    assert len(listings) >= 9
    assert len(history_rows) >= len(listings)
    assert len(watchlist_rows) >= 3
    assert all(p.image_url and p.image_url.startswith("https://") for p in products)
    assert all(lst.image_url and lst.image_url.startswith("https://") for lst in listings)


def test_seed_all_is_idempotent(db_session: Session) -> None:
    seed_all(db_session)
    first_counts = (
        db_session.query(User).count(),
        db_session.query(SiteConfig).count(),
        db_session.query(CanonicalProduct).count(),
        db_session.query(ProductListing).count(),
        db_session.query(PriceHistory).count(),
        db_session.query(WatchlistItem).count(),
        db_session.query(AdapterRunLog).count(),
    )

    seed_all(db_session)
    second_counts = (
        db_session.query(User).count(),
        db_session.query(SiteConfig).count(),
        db_session.query(CanonicalProduct).count(),
        db_session.query(ProductListing).count(),
        db_session.query(PriceHistory).count(),
        db_session.query(WatchlistItem).count(),
        db_session.query(AdapterRunLog).count(),
    )

    assert first_counts == second_counts


def test_seeded_demo_credentials_verify_against_bcrypt(db_session: Session) -> None:
    seed_all(db_session)

    admin = db_session.query(User).filter_by(email=settings.SEED_ADMIN_EMAIL).one()
    demo_user = db_session.query(User).filter_by(email=settings.SEED_USER_EMAIL).one()

    assert verify_password(settings.SEED_ADMIN_PASSWORD, admin.password_hash) is True
    assert verify_password(settings.SEED_USER_PASSWORD, demo_user.password_hash) is True
    assert verify_password("incorrect-password", admin.password_hash) is False
