from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.db.base import Base, utcnow


class SiteConfig(Base):
    """Polite polling and circuit breaker configuration per retailer."""

    __tablename__ = "site_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    polling_interval_minutes: Mapped[int] = mapped_column(
        Integer, default=settings.DEFAULT_POLLING_INTERVAL_MINUTES, nullable=False
    )
    min_delay_seconds: Mapped[int] = mapped_column(
        Integer, default=settings.DEFAULT_MIN_DELAY_SECONDS, nullable=False
    )
    max_requests_per_hour: Mapped[int] = mapped_column(
        Integer, default=settings.DEFAULT_MAX_REQUESTS_PER_HOUR, nullable=False
    )
    circuit_breaker_open: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
