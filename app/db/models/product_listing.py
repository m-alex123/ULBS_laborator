from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime

if TYPE_CHECKING:
    from app.db.models.canonical_product import CanonicalProduct
    from app.db.models.notification_log import NotificationLog
    from app.db.models.price_history import PriceHistory


class ProductListing(Base):
    """Retailer-specific product offer tied to a CanonicalProduct."""

    __tablename__ = "product_listings"
    __table_args__ = (
        UniqueConstraint("canonical_product_id", "store", name="uq_listing_product_store"),
        CheckConstraint(
            "store IN ('jdsports', 'sizeer', 'buzzsneakers')",
            name="ck_product_listings_store",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    canonical_product_id: Mapped[int] = mapped_column(
        ForeignKey("canonical_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    store: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False)
    current_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    original_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    raw_title: Mapped[str] = mapped_column(String(512), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="RON", nullable=False)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    match_needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    match_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    suggested_canonical_product_id: Mapped[int | None] = mapped_column(
        ForeignKey("canonical_products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    canonical_product: Mapped["CanonicalProduct"] = relationship(
        back_populates="listings",
        foreign_keys=[canonical_product_id],
    )
    price_history: Mapped[list["PriceHistory"]] = relationship(
        back_populates="product_listing",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    notification_logs: Mapped[list["NotificationLog"]] = relationship(
        back_populates="product_listing",
        passive_deletes=True,
    )
