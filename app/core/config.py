from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DEV_SECRET_KEY = "dev-only-change-before-production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables or defaults."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: str = "development"
    APP_NAME: str = "P23 Ethical Sneaker Price Monitor"
    DATABASE_URL: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'pricemonitor.db'}"
    SNAPSHOTS_DIR: Path = PROJECT_ROOT / "storage" / "snapshots"
    SECRET_KEY: str = _DEV_SECRET_KEY
    SESSION_COOKIE_NAME: str = "p23_session"
    SESSION_MAX_AGE_SECONDS: int = Field(default=60 * 60 * 24 * 7, gt=0)

    # Ethical scraping & politeness policy (D-002)
    USER_AGENT: str = (
        "ULBS-Web2-PriceMonitor/1.0 (+https://github.com/m-alex123/ULBS_laborator)"
    )
    SUPPORTED_STORES: tuple[str, ...] = ("jdsports", "sizeer", "buzzsneakers")
    DEFAULT_POLLING_INTERVAL_MINUTES: int = Field(default=360, gt=0)
    DEFAULT_MIN_DELAY_SECONDS: int = Field(default=10, ge=10)
    DEFAULT_MAX_REQUESTS_PER_HOUR: int = Field(default=30, ge=1, le=30)
    ROBOTS_CACHE_TTL_HOURS: int = Field(default=24, ge=1)

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

    @model_validator(mode="after")
    def validate_production_secret(self) -> "Settings":
        """Enforce strong SECRET_KEY and non-default seed passwords in production/staging."""
        env = self.ENVIRONMENT.strip().lower()
        self.ENVIRONMENT = env
        if env in {"production", "prod", "staging"}:
            secret = self.SECRET_KEY.strip()
            weak_secrets = {
                "",
                _DEV_SECRET_KEY,
                "replace-with-strong-random-secret-key",
            }
            if secret in weak_secrets or len(secret) < 32:
                raise ValueError(
                    "SECRET_KEY must be at least 32 characters and non-default in production/staging"
                )
        return self


settings = Settings()
