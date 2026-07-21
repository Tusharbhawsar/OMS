from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.customer import Customer, CustomerServicePoint, ServicePoint
from app.models.outage import OutageCircuitMap, OutageCustomerMap, OutageEvent
from app.models.reference import ChannelMaster, CustomerType
from app.repositories.base import BaseRepository


class OutageRepository(BaseRepository[OutageEvent]):
    """Repository for outage events and affected customer mappings."""

    # Ye constructor database session ko repository ke andar store karta hai.
    # Baad me isi self.db ke through outage, customer mapping aur count wali queries chalti hain.
    def __init__(self, db: Session) -> None:
        self.db = db

    # Ye function outage_id ke basis par ek specific outage event database se nikalta hai.
    # Agar us id ka outage nahi milta, to None return hota hai.
    def get_by_id(self, outage_id: str) -> OutageEvent | None:
        return self.db.get(OutageEvent, outage_id)

    # Ye function sirf un outages ko fetch karta hai jinka status Active ya Scheduled hai.
    # Result ko start_time ke ascending order me sort karta hai, yani jo outage pehle start hoga wo pehle aayega.
    def list_active(self) -> list[OutageEvent]:
        stmt = select(OutageEvent).where(OutageEvent.status.in_(["Active", "Scheduled"])).order_by(OutageEvent.start_time.asc())
        return list(self.db.scalars(stmt).all())

    # Ye function ek time range me aane wale saare outages fetch karta hai (status filter ke bina).
    # Ek outage range me tab maana jaata hai jab uska start_time diye gaye start aur end ke beech aata hai.
    # Optional taur par end bound diya ja sakta hai; agar end None hai to sirf start se aage ke outages aate hain.
    def list_in_time_range(self, range_start: datetime, range_end: datetime | None = None) -> list[OutageEvent]:
        stmt = select(OutageEvent).where(OutageEvent.start_time >= range_start)
        if range_end is not None:
            stmt = stmt.where(OutageEvent.start_time <= range_end)
        stmt = stmt.order_by(OutageEvent.start_time.asc())
        return list(self.db.scalars(stmt).all())

    # Ye function Planned type ke outages me se due/current outages nikalta hai.
    # Sirf Planned outages consider karta hai aur unme status Active ya Scheduled hona chahiye.
    def list_planned_due(self) -> list[OutageEvent]:
        stmt = (
            select(OutageEvent)
            .where(OutageEvent.outage_type == "Planned")
            .where(OutageEvent.status.in_(["Active", "Scheduled"]))
            .order_by(OutageEvent.start_time.asc())
        )
        return list(self.db.scalars(stmt).all())

    # Ye function planned outage lifecycle job ke liye candidate outages fetch karta hai.
    # Isme Active, Scheduled, Restored, Resolved, Cancelled status wale outages aate hain,
    # aur agar cancellation_flag true hai to wo outage bhi lifecycle processing ke liye include hota hai.
    def list_planned_lifecycle_candidates(self) -> list[OutageEvent]:
        stmt = (
            select(OutageEvent)
            .where(OutageEvent.outage_type == "Planned")
            .where(
                (OutageEvent.status.in_(["Active", "Scheduled", "Restored", "Resolved", "Cancelled"]))
                | (OutageEvent.cancellation_flag.is_(True))
            )
            .order_by(OutageEvent.start_time.asc())
        )
        return list(self.db.scalars(stmt).all())

    # Ye function outage aur customer ke beech mapping create karta hai.
    # Pehle check karta hai ki same outage_id aur customer_id ka record already exist to nahi hai.
    # Agar mapping nahi hai, to new mapping add karta hai aur notification/restored flags default false rakhta hai.
    def upsert_outage_customer(self, outage_id: str, customer_id: str) -> None:
        existing = self.db.get(OutageCustomerMap, {"outage_id": outage_id, "customer_id": customer_id})
        if existing is None:
            self.db.add(OutageCustomerMap(outage_id=outage_id, customer_id=customer_id, notification_flag=False, restored_flag=False))

    # Ye function kisi customer ke outage mapping me notification_flag true karta hai.
    # Iska matlab hota hai ki is customer ko outage notification bheja ja chuka hai.
    # Agar mapping record milta hi nahi hai, to function kuch change nahi karta.
    def mark_customer_notified(self, outage_id: str, customer_id: str) -> None:
        mapping = self.db.get(OutageCustomerMap, {"outage_id": outage_id, "customer_id": customer_id})
        if mapping:
            mapping.notification_flag = True

    # Ye function ek outage ke affected customers ki final list return karta hai.
    # Pehle direct outage-customer mapping check karta hai; agar customers mil jaate hain to wahi return karta hai.
    # Agar direct mapping empty ho, tab circuit/transformer mapping ke basis par affected customers calculate karta hai.
    def get_affected_customers(self, outage_id: str) -> list[dict[str, object]]:
        """Return affected customers sorted by Medical Baseline and priority."""
        mapped_customers = self.get_mapped_affected_customers(outage_id)
        if mapped_customers:
            return mapped_customers
        return self.get_circuit_affected_customers(outage_id)

    # Ye function un customers ki details fetch karta hai jo directly outage ke saath mapped hain.
    # Query customer, service point, customer type aur notification channel tables ko join karti hai.
    # Sirf active customers include hote hain, aur sorting medical baseline customers ko pehle priority deti hai.
    def get_mapped_affected_customers(self, outage_id: str) -> list[dict[str, object]]:
        """Return customers explicitly mapped to an outage."""
        stmt = (
            select(
                Customer.customer_id,
                Customer.first_name,
                Customer.last_name,
                Customer.email,
                Customer.phone,
                Customer.preferred_language,
                ServicePoint.service_point_id,
                ServicePoint.circuit_id,
                ServicePoint.transformer_id,
                ServicePoint.geographic_region,
                CustomerServicePoint.is_medical_baseline,
                CustomerType.type_name,
                CustomerType.priority,
                ChannelMaster.channel_id,
                ChannelMaster.channel_name,
            )
            .join(OutageCustomerMap, OutageCustomerMap.customer_id == Customer.customer_id)
            .join(CustomerServicePoint, CustomerServicePoint.customer_id == Customer.customer_id)
            .join(ServicePoint, ServicePoint.service_point_id == CustomerServicePoint.service_point_id)
            .join(CustomerType, CustomerType.customer_type_id == CustomerServicePoint.customer_type_id)
            .join(ChannelMaster, ChannelMaster.channel_id == CustomerServicePoint.channel_id)
            .where(OutageCustomerMap.outage_id == outage_id)
            .where(Customer.is_active.is_(True))
            .order_by(CustomerServicePoint.is_medical_baseline.desc(), CustomerType.priority.asc(), Customer.customer_id.asc())
        )
        rows = self.db.execute(stmt).mappings().all()
        return [dict(row) for row in rows]

    # Ye function direct customer mapping na hone par affected customers infer karta hai.
    # OutageCircuitMap me outage ka circuit_id aur transformer_id hota hai; un values ko ServicePoint se match karke
    # pata lagaya jaata hai ki kaunse active customers us circuit/transformer se connected hain.
    def get_circuit_affected_customers(self, outage_id: str) -> list[dict[str, object]]:
        """Return customers inferred from outage circuit/transformer mapping."""
        stmt = (
            select(
                Customer.customer_id,
                Customer.first_name,
                Customer.last_name,
                Customer.email,
                Customer.phone,
                Customer.preferred_language,
                ServicePoint.service_point_id,
                ServicePoint.circuit_id,
                ServicePoint.transformer_id,
                ServicePoint.geographic_region,
                CustomerServicePoint.is_medical_baseline,
                CustomerType.type_name,
                CustomerType.priority,
                ChannelMaster.channel_id,
                ChannelMaster.channel_name,
            )
            .join(CustomerServicePoint, CustomerServicePoint.customer_id == Customer.customer_id)
            .join(ServicePoint, ServicePoint.service_point_id == CustomerServicePoint.service_point_id)
            .join(CustomerType, CustomerType.customer_type_id == CustomerServicePoint.customer_type_id)
            .join(ChannelMaster, ChannelMaster.channel_id == CustomerServicePoint.channel_id)
            .join(
                OutageCircuitMap,
                (OutageCircuitMap.circuit_id == ServicePoint.circuit_id)
                & (OutageCircuitMap.transformer_id == ServicePoint.transformer_id),
            )
            .where(OutageCircuitMap.outage_id == outage_id)
            .where(Customer.is_active.is_(True))
            .order_by(CustomerServicePoint.is_medical_baseline.desc(), CustomerType.priority.asc(), Customer.customer_id.asc())
        )
        rows = self.db.execute(stmt).mappings().all()
        return [dict(row) for row in rows]

    # Ye function dashboard/summary ke liye current active outage count return karta hai.
    # Count me sirf Active aur Scheduled status wale outages include kiye jaate hain.
    def count_active(self) -> int:
        return int(self.db.scalar(select(func.count()).select_from(OutageEvent).where(OutageEvent.status.in_(["Active", "Scheduled"]))) or 0)

    # Ye function OutageEvent table me jitne bhi outage records hain unka total count return karta hai.
    # Isme status ka filter nahi hai, isliye Active, Scheduled, Resolved, Cancelled sab records count hote hain.
    def count_total(self) -> int:
        return int(self.db.scalar(select(func.count()).select_from(OutageEvent)) or 0)
