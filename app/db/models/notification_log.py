from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow

if TYPE_CHECKING:
    from app.db.models.product_listing import ProductListing
    from app.db.models.user import User


class NotificationLog(Base):
    """Audit record of an email or Telegram alert dispatched to a user."""

    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_listing_id: Mapped[int] = mapped_column(
        ForeignKey("product_listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    trigger_reason: Mapped[str] = mapped_column(String(100), nullable=False)
    message_payload: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="notification_logs")
    product_listing: Mapped["ProductListing"] = relationship(back_populates="notification_logs")
