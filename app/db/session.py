from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine, create_engine, event, text
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


def create_db_engine(database_url: str | None = None) -> Engine:
    """Build a SQLAlchemy engine configured for SQLite (with FK enforcement) or PostgreSQL."""
    url = database_url or settings.DATABASE_URL
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


def init_db(target_engine: Engine | None = None, create_snapshots_dir: bool = True) -> None:
    """Ensure local storage directories exist and create all database tables."""
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
    Base.metadata.create_all(bind=bound_engine)
