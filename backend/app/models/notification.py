from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.utils.time import ist_now


class Notification(Base):
    """Notification record for every customer communication attempt."""

    __tablename__ = "notification"

    notification_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    outage_id: Mapped[str] = mapped_column(ForeignKey("outage_event.outage_id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customer.customer_id", ondelete="CASCADE"), index=True)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    channel_id: Mapped[str] = mapped_column(ForeignKey("channel_master.channel_id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Pending", index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime)
    message_content: Mapped[str] = mapped_column(Text, nullable=False)

    outage = relationship("OutageEvent", back_populates="notifications")
    customer = relationship("Customer", back_populates="notifications")
    channel = relationship("ChannelMaster", back_populates="notifications")
    attempts = relationship("NotificationAttempt", back_populates="notification", cascade="all, delete-orphan")


class NotificationAttempt(Base):
    """Provider-level delivery attempt audit for retries and debugging."""

    __tablename__ = "notification_attempt"

    attempt_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    notification_id: Mapped[str] = mapped_column(ForeignKey("notification.notification_id", ondelete="CASCADE"), index=True)
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=ist_now, server_default=func.now(), nullable=False)

    notification = relationship("Notification", back_populates="attempts")
