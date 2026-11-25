from datetime import datetime

from sqlalchemy import CheckConstraint, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UTCDateTime, utcnow


class AdapterRunLog(Base):
    """Execution outcome and diagnostic snapshot reference for a store adapter."""

    __tablename__ = "adapter_run_logs"
    __table_args__ = (
        CheckConstraint(
            "store IN ('jdsports', 'sizeer', 'buzzsneakers')",
            name="ck_adapter_run_logs_store",
        ),
        CheckConstraint(
            "status IN ('success', 'failed', 'suspect')",
            name="ck_adapter_run_logs_status",
        ),
        Index("ix_adapter_run_logs_store_created", "store", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    snapshot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, nullable=False, index=True
    )
