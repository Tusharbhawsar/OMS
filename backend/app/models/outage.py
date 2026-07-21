from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.utils.time import ist_now


class OutageEvent(Base):
    """Core outage record from ADMS/OMS or planned outage schedule."""

    __tablename__ = "outage_event"

    outage_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    outage_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    estimated_end_time: Mapped[datetime | None] = mapped_column(DateTime)
    actual_end_time: Mapped[datetime | None] = mapped_column(DateTime)
    etr_predicted_by_ml: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cancellation_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Set when a cancellation event arrives (Option 3). Null until then; gives cancellation
    # its own timestamp, parallel to actual_end_time for restoration.
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=ist_now, server_default=func.now(), nullable=False)

    circuits = relationship("OutageCircuitMap", back_populates="outage", cascade="all, delete-orphan")
    customers = relationship("OutageCustomerMap", back_populates="outage", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="outage")


class OutageCircuitMap(Base):
    """Junction table linking an outage to affected circuits and transformers."""

    __tablename__ = "outage_circuit_map"

    outage_id: Mapped[str] = mapped_column(ForeignKey("outage_event.outage_id", ondelete="CASCADE"), primary_key=True)
    circuit_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    transformer_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    affected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    linked_at: Mapped[datetime] = mapped_column(DateTime, default=ist_now, server_default=func.now(), nullable=False)

    outage = relationship("OutageEvent", back_populates="circuits")


class OutageCustomerMap(Base):
    """Junction table linking each outage to affected customers."""

    __tablename__ = "outage_customer_map"

    outage_id: Mapped[str] = mapped_column(ForeignKey("outage_event.outage_id", ondelete="CASCADE"), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customer.customer_id", ondelete="CASCADE"), primary_key=True)
    notification_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    restored_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    outage = relationship("OutageEvent", back_populates="customers")
    customer = relationship("Customer", back_populates="outage_maps")


class RawOutageEvent(Base):
    """Raw uploaded/streamed outage payload retained for audit and replay in Phase 1."""

    __tablename__ = "raw_outage_event"

    raw_event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    external_event_id: Mapped[str | None] = mapped_column(String(100), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=ist_now, server_default=func.now(), nullable=False)
