from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db.session import init_db
from app.web.routers import auth, health, watchlist

WEB_DIR = Path(__file__).resolve().parent / "web"


def create_app(run_init_db: bool = True) -> FastAPI:
    """Create and configure the FastAPI web application."""

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if run_init_db:
            init_db()
        yield

    application = FastAPI(
        title=settings.APP_NAME,
        version="0.2.0",
        lifespan=lifespan,
    )

    application.mount(
        "/static",
        StaticFiles(directory=str(WEB_DIR / "static")),
        name="static",
    )

    application.include_router(health.router)
    application.include_router(auth.router)
    application.include_router(watchlist.router)

    return application


app = create_app()
