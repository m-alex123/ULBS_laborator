from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime, utcnow

if TYPE_CHECKING:
    from app.db.models.product_listing import ProductListing
    from app.db.models.watchlist_item import WatchlistItem


class CanonicalProduct(Base):
    """Store-agnostic sneaker entity deduplicated across retailers by SKU."""

    __tablename__ = "canonical_products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[str] = mapped_column(String(100), nullable=False)
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, nullable=False
    )

    listings: Mapped[list["ProductListing"]] = relationship(
        back_populates="canonical_product",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    watchlist_items: Mapped[list["WatchlistItem"]] = relationship(
        back_populates="canonical_product",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
