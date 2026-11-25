from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow

if TYPE_CHECKING:
    from app.db.models.canonical_product import CanonicalProduct
    from app.db.models.user import User


class WatchlistItem(Base):
    """User watchlist subscription and alert rules for a CanonicalProduct."""

    __tablename__ = "watchlist_items"
    __table_args__ = (
        UniqueConstraint("user_id", "canonical_product_id", name="uq_watchlist_user_product"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    canonical_product_id: Mapped[int] = mapped_column(
        ForeignKey("canonical_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_discount_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notify_stock: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_email: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_telegram: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="watchlist_items")
    canonical_product: Mapped["CanonicalProduct"] = relationship(back_populates="watchlist_items")
