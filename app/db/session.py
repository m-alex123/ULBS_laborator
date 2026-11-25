from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Connection, Engine, create_engine, event, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base


def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
    """Enforce SQLite foreign key constraints on every new DBAPI connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def normalize_database_url(url: str) -> str:
    """Normalize PostgreSQL URLs to use the installed psycopg v3 driver."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def create_db_engine(database_url: str | None = None) -> Engine:
    """Build a SQLAlchemy engine configured for SQLite (with FK enforcement) or PostgreSQL."""
    url = normalize_database_url(database_url or settings.DATABASE_URL)
    is_sqlite = url.startswith("sqlite")
    engine_kwargs: dict[str, object] = {
        "connect_args": {"check_same_thread": False} if is_sqlite else {},
    }
    if not is_sqlite:
        engine_kwargs["pool_pre_ping"] = True
    new_engine = create_engine(url, **engine_kwargs)
    if new_engine.dialect.name == "sqlite":
        event.listen(new_engine, "connect", _set_sqlite_pragma)
    return new_engine


engine = create_db_engine()
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for request-scoped dependencies."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection(db: Session) -> bool:
    """Verify database connectivity with a lightweight SELECT 1 query."""
    try:
        db.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False


_ADDITIVE_MIGRATIONS: tuple[tuple[str, str, str, str], ...] = (
    # (table_name, column_name, postgres_ddl, sqlite_ddl)
    (
        "users",
        "email_enabled",
        "BOOLEAN NOT NULL DEFAULT TRUE",
        "BOOLEAN NOT NULL DEFAULT 1",
    ),
    (
        "users",
        "telegram_enabled",
        "BOOLEAN NOT NULL DEFAULT FALSE",
        "BOOLEAN NOT NULL DEFAULT 0",
    ),
    (
        "site_configs",
        "adapter_status",
        "VARCHAR(20) NOT NULL DEFAULT 'healthy'",
        "VARCHAR(20) NOT NULL DEFAULT 'healthy'",
    ),
    (
        "product_listings",
        "match_needs_review",
        "BOOLEAN NOT NULL DEFAULT FALSE",
        "BOOLEAN NOT NULL DEFAULT 0",
    ),
    (
        "product_listings",
        "match_confidence",
        "DOUBLE PRECISION",
        "FLOAT",
    ),
    (
        "product_listings",
        "suggested_canonical_product_id",
        "INTEGER REFERENCES canonical_products(id) ON DELETE SET NULL",
        "INTEGER REFERENCES canonical_products(id) ON DELETE SET NULL",
    ),
)


def _apply_additive_schema_migrations(conn: Connection) -> None:
    """Idempotently add Step 3+ columns to pre-existing PostgreSQL or SQLite tables."""
    inspector = inspect(conn)
    is_postgres = conn.dialect.name == "postgresql"
    columns_by_table: dict[str, set[str]] = {}

    for table_name, col_name, pg_ddl, sqlite_ddl in _ADDITIVE_MIGRATIONS:
        if not inspector.has_table(table_name):
            continue
        if is_postgres:
            conn.execute(
                text(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {col_name} {pg_ddl}")
            )
            continue

        existing = columns_by_table.get(table_name)
        if existing is None:
            existing = {col["name"] for col in inspector.get_columns(table_name)}
            columns_by_table[table_name] = existing
        if col_name not in existing:
            conn.execute(
                text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {sqlite_ddl}")
            )
            existing.add(col_name)

    if inspector.has_table("product_listings"):
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_product_listings_suggested_canonical_product_id "
                "ON product_listings (suggested_canonical_product_id)"
            )
        )


def init_db(target_engine: Engine | None = None, create_snapshots_dir: bool = True) -> None:
    """Ensure local storage directories exist and create/upgrade all database tables."""
    import app.db.models  # noqa: F401  # Register all ORM models on Base.metadata

    bound_engine = target_engine or engine
    parsed_url = make_url(str(bound_engine.url))
    if (
        parsed_url.drivername.startswith("sqlite")
        and parsed_url.database not in (None, "", ":memory:")
    ):
        Path(parsed_url.database).parent.mkdir(parents=True, exist_ok=True)

    if create_snapshots_dir:
        settings.SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    if bound_engine.dialect.name == "postgresql":
        with bound_engine.begin() as conn:
            conn.execute(text("SELECT pg_advisory_xact_lock(23001)"))
            Base.metadata.create_all(bind=conn)
            _apply_additive_schema_migrations(conn)
    else:
        Base.metadata.create_all(bind=bound_engine)
        with bound_engine.begin() as conn:
            _apply_additive_schema_migrations(conn)
