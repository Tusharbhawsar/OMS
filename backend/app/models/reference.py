from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CustomerType(Base):
    """Customer priority/segmentation master table."""

    __tablename__ = "customer_type"

    customer_type_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    type_name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=99)
    description: Mapped[str | None] = mapped_column(String(200))

    customer_service_points = relationship("CustomerServicePoint", back_populates="customer_type")


class ChannelMaster(Base):
    """Notification channel master table."""

    __tablename__ = "channel_master"

    channel_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    channel_name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    customer_service_points = relationship("CustomerServicePoint", back_populates="channel")
    notifications = relationship("Notification", back_populates="channel")
