from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.utils.time import ist_now


class Customer(Base):
    """Customer account details sourced from CC&B."""

    __tablename__ = "customer"

    customer_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    account_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(50))
    # ISO-639-1 language code (e.g. "en", "es") driving the language of generated
    # notification messages. Defaults to English so existing rows stay valid.
    preferred_language: Mapped[str] = mapped_column(String(10), nullable=False, default="en", server_default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=ist_now, server_default=func.now(), nullable=False)

    service_points = relationship("CustomerServicePoint", back_populates="customer", cascade="all, delete-orphan")
    outage_maps = relationship("OutageCustomerMap", back_populates="customer")
    notifications = relationship("Notification", back_populates="customer")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class ServicePoint(Base):
    """Physical grid service point mapped to circuit/transformer/geography."""

    __tablename__ = "service_point"

    service_point_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    circuit_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    transformer_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    geographic_region: Mapped[str | None] = mapped_column(String(100), index=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6))

    customers = relationship("CustomerServicePoint", back_populates="service_point")


class CustomerServicePoint(Base):
    """Junction table connecting customer, service point, type, and preferred channel."""

    __tablename__ = "customer_service_point"

    customer_id: Mapped[str] = mapped_column(ForeignKey("customer.customer_id", ondelete="CASCADE"), primary_key=True)
    service_point_id: Mapped[str] = mapped_column(ForeignKey("service_point.service_point_id", ondelete="CASCADE"), primary_key=True)
    customer_type_id: Mapped[str] = mapped_column(ForeignKey("customer_type.customer_type_id"), nullable=False)
    channel_id: Mapped[str] = mapped_column(ForeignKey("channel_master.channel_id"), nullable=False)
    is_medical_baseline: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    linked_at: Mapped[datetime] = mapped_column(DateTime, default=ist_now, server_default=func.now(), nullable=False)

    customer = relationship("Customer", back_populates="service_points")
    service_point = relationship("ServicePoint", back_populates="customers")
    customer_type = relationship("CustomerType", back_populates="customer_service_points")
    channel = relationship("ChannelMaster", back_populates="customer_service_points")
