from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.db.base import Base, UTCDateTime, utcnow


class SiteConfig(Base):
    """Polite polling and circuit breaker configuration per retailer."""

    __tablename__ = "site_configs"
    __table_args__ = (
        CheckConstraint(
            "store IN ('jdsports', 'sizeer', 'buzzsneakers')",
            name="ck_site_configs_store",
        ),
        CheckConstraint(
            "polling_interval_minutes > 0",
            name="ck_site_configs_polling_interval",
        ),
        CheckConstraint(
            "min_delay_seconds >= 10",
            name="ck_site_configs_min_delay",
        ),
        CheckConstraint(
            "max_requests_per_hour >= 1 AND max_requests_per_hour <= 30",
            name="ck_site_configs_max_req",
        ),
        CheckConstraint(
            "adapter_status IN ('healthy', 'suspect', 'degraded', 'circuit_open')",
            name="ck_site_configs_adapter_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    polling_interval_minutes: Mapped[int] = mapped_column(
        Integer,
        default=lambda: settings.DEFAULT_POLLING_INTERVAL_MINUTES,
        nullable=False,
    )
    min_delay_seconds: Mapped[int] = mapped_column(
        Integer,
        default=lambda: settings.DEFAULT_MIN_DELAY_SECONDS,
        nullable=False,
    )
    max_requests_per_hour: Mapped[int] = mapped_column(
        Integer,
        default=lambda: settings.DEFAULT_MAX_REQUESTS_PER_HOUR,
        nullable=False,
    )
    adapter_status: Mapped[str] = mapped_column(
        String(20), default="healthy", nullable=False
    )
    circuit_breaker_open: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, onupdate=utcnow, nullable=False
    )
