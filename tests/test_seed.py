from sqlalchemy.orm import Session, sessionmaker

import app.db.seed as seed_module
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
from app.db.session import create_db_engine


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


def test_seed_all_three_times_and_partial_adapter_logs_idempotent(db_session: Session) -> None:
    # Pre-seed a single store log to verify partial seed fills the remaining stores
    db_session.add(AdapterRunLog(store="jdsports", status="success", duration_ms=150))
    db_session.commit()

    for _ in range(3):
        seed_all(db_session)

    assert db_session.query(AdapterRunLog).count() == 3
    assert {log.store for log in db_session.query(AdapterRunLog).all()} == {
        "jdsports",
        "sizeer",
        "buzzsneakers",
    }
    assert db_session.query(PriceHistory).count() == 45


def test_seed_main_cli_initializes_and_seeds_sqlite_file(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "cli_seed.db"
    snapshots_dir = tmp_path / "snapshots"
    cli_engine = create_db_engine(f"sqlite:///{db_path}")
    CliSessionLocal = sessionmaker(
        bind=cli_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    monkeypatch.setattr(settings, "SNAPSHOTS_DIR", snapshots_dir)
    monkeypatch.setattr(seed_module, "SessionLocal", CliSessionLocal)
    monkeypatch.setattr(
        seed_module,
        "init_db",
        lambda: seed_module.init_db.__wrapped__(cli_engine)
        if hasattr(seed_module.init_db, "__wrapped__")
        else __import__("app.db.session", fromlist=["init_db"]).init_db(cli_engine),
    )

    try:
        seed_module.main()
        seed_module.main()

        with CliSessionLocal() as session:
            assert session.query(User).count() == 2
            assert session.query(SiteConfig).count() == 3
            assert session.query(CanonicalProduct).count() == 3
            assert session.query(ProductListing).count() == 9
            assert session.query(PriceHistory).count() == 45
            assert session.query(AdapterRunLog).count() == 3
    finally:
        cli_engine.dispose()
