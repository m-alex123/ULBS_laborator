from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db.session import engine, init_db
from app.web.routers import auth, health, watchlist

WEB_DIR = Path(__file__).resolve().parent / "web"
_PROD_ENVS = {"production", "prod", "staging"}


def create_app(run_init_db: bool = True) -> FastAPI:
    """Create and configure the FastAPI web application."""

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if run_init_db:
            init_db()
        try:
            yield
        finally:
            engine.dispose()

    is_prod_like = settings.ENVIRONMENT.strip().lower() in _PROD_ENVS
    application = FastAPI(
        title=settings.APP_NAME,
        version="0.2.0",
        lifespan=lifespan,
        docs_url=None if is_prod_like else "/docs",
        redoc_url=None if is_prod_like else "/redoc",
        openapi_url=None if is_prod_like else "/openapi.json",
    )

    @application.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

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
