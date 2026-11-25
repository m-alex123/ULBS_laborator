from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime, utcnow

if TYPE_CHECKING:
    from app.db.models.product_listing import ProductListing


class PriceHistory(Base):
    """Historical price and stock observation for a ProductListing."""

    __tablename__ = "price_history"
    __table_args__ = (
        CheckConstraint(
            "status IN ('valid', 'suspect', 'error')",
            name="ck_price_history_status",
        ),
        Index("ix_price_history_listing_recorded", "product_listing_id", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_listing_id: Mapped[int] = mapped_column(
        ForeignKey("product_listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="RON", nullable=False)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="valid", nullable=False)

    product_listing: Mapped["ProductListing"] = relationship(back_populates="price_history")
