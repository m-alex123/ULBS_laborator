from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow


class AdapterRunLog(Base):
    """Execution outcome and diagnostic snapshot reference for a store adapter."""

    __tablename__ = "adapter_run_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    snapshot_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )
