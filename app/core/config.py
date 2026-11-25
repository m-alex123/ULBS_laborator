from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables or defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "P23 Ethical Sneaker Price Monitor"
    DATABASE_URL: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'pricemonitor.db'}"
    SNAPSHOTS_DIR: Path = PROJECT_ROOT / "storage" / "snapshots"
    SECRET_KEY: str = "dev-only-change-before-production"

    # Ethical scraping & politeness policy (D-002)
    USER_AGENT: str = (
        "ULBS-Web2-PriceMonitor/1.0 (+https://github.com/m-alex123/ULBS_laborator)"
    )
    SUPPORTED_STORES: tuple[str, ...] = ("jdsports", "sizeer", "buzzsneakers")
    DEFAULT_POLLING_INTERVAL_MINUTES: int = 360
    DEFAULT_MIN_DELAY_SECONDS: int = 10
    DEFAULT_MAX_REQUESTS_PER_HOUR: int = 30
    ROBOTS_CACHE_TTL_HOURS: int = 24

    # Drift detection thresholds (D-002)
    DRIFT_MAX_DROP_PERCENT: float = 70.0
    DRIFT_MAX_RISE_PERCENT: float = 200.0
    DRIFT_MIN_VALID_PRICE_RON: float = 50.0
    DRIFT_MIN_TITLE_SIMILARITY: float = 0.60

    # External notification channels (optional)
    TELEGRAM_BOT_TOKEN: str | None = None
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str | None = None

    # Demo seed accounts (D-003)
    SEED_ADMIN_EMAIL: str = "admin@pricemonitor.local"
    SEED_ADMIN_PASSWORD: str = "Admin123!"
    SEED_USER_EMAIL: str = "user@pricemonitor.local"
    SEED_USER_PASSWORD: str = "User123!"


settings = Settings()
