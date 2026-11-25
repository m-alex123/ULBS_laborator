from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime, utcnow

if TYPE_CHECKING:
    from app.db.models.product_listing import ProductListing
    from app.db.models.user import User


class NotificationLog(Base):
    """Audit record of an email or Telegram alert dispatched to a user."""

    __tablename__ = "notification_logs"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('email', 'telegram')",
            name="ck_notification_logs_channel",
        ),
        Index("ix_notification_logs_user_sent", "user_id", "sent_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_listing_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_listings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    trigger_reason: Mapped[str] = mapped_column(String(100), nullable=False)
    message_payload: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="notification_logs")
    product_listing: Mapped["ProductListing | None"] = relationship(
        back_populates="notification_logs"
    )
