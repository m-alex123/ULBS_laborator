from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record) -> None:
    """Enforce SQLite foreign key constraints on every new DBAPI connection."""
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_db_engine(database_url: str | None = None) -> Engine:
    """Build a SQLAlchemy engine configured for SQLite or a custom URL."""
    url = database_url or settings.DATABASE_URL
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, future=True)


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


def init_db(target_engine: Engine | None = None) -> None:
    """Ensure local storage directories exist and create all database tables."""
    import app.db.models  # noqa: F401  # Register all ORM models on Base.metadata

    bound_engine = target_engine or engine
    parsed_url = make_url(str(bound_engine.url))
    if parsed_url.drivername.startswith("sqlite") and parsed_url.database not in (None, "", ":memory:"):
        Path(parsed_url.database).parent.mkdir(parents=True, exist_ok=True)

    settings.SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=bound_engine)
