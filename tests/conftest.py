from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session, sessionmaker

import app.db.models  # noqa: F401
from app.db.base import Base
from app.db.session import create_db_engine


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """Provide an isolated SQLite database session with foreign keys enabled."""
    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
