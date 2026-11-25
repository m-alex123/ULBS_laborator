from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.canonical_product import CanonicalProduct
    from app.db.models.notification_log import NotificationLog
    from app.db.models.price_history import PriceHistory


class ProductListing(Base):
    """Retailer-specific product offer tied to a CanonicalProduct."""

    __tablename__ = "product_listings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    canonical_product_id: Mapped[int] = mapped_column(
        ForeignKey("canonical_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    store: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False)
    current_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    original_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    raw_title: Mapped[str] = mapped_column(String(512), nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="RON", nullable=False)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    canonical_product: Mapped["CanonicalProduct"] = relationship(back_populates="listings")
    price_history: Mapped[list["PriceHistory"]] = relationship(
        back_populates="product_listing",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    notification_logs: Mapped[list["NotificationLog"]] = relationship(
        back_populates="product_listing",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
