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


@pytest.fixture()
def client(tmp_path):
    """Provide a FastAPI TestClient wired to an isolated file-backed SQLite database."""
    from fastapi.testclient import TestClient

    from app.db.seed import seed_all
    from app.db.session import get_db
    from app.main import create_app

    db_file = tmp_path / "web_test.db"
    test_engine = create_db_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    with TestingSessionLocal() as seed_session:
        seed_all(seed_session)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = create_app(run_init_db=False)
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client, TestingSessionLocal
    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()
