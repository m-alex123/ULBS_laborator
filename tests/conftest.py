from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session, sessionmaker

import app.db.models  # noqa: F401
from app.core.config import settings
from app.db.base import Base
from app.db.session import create_db_engine


@pytest.fixture(autouse=True)
def isolate_snapshots_dir(tmp_path, monkeypatch) -> None:
    """Keep tests from touching the workspace storage/snapshots directory."""
    monkeypatch.setattr(settings, "SNAPSHOTS_DIR", tmp_path / "snapshots")


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
