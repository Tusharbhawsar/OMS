from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.customer import Customer, CustomerServicePoint, ServicePoint
from app.models.outage import OutageCircuitMap, OutageCustomerMap, OutageEvent
from app.models.reference import ChannelMaster, CustomerType
from app.repositories.outage_repository import OutageRepository


def test_affected_customers_prefers_explicit_outage_customer_map() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        db.add_all(
            [
                CustomerType(customer_type_id="CT002", type_name="Commercial", priority=2),
                CustomerType(customer_type_id="CT003", type_name="Residential", priority=3),
                CustomerType(customer_type_id="CT004", type_name="Industrial", priority=4),
                ChannelMaster(channel_id="CH001", channel_name="Email", is_active=True),
                OutageEvent(
                    outage_id="OTG00005",
                    outage_type="Unplanned",
                    status="Active",
                    start_time=datetime(2025, 1, 8, 11, 56),
                    estimated_end_time=datetime(2025, 1, 8, 17, 56),
                    etr_predicted_by_ml=True,
                    cancellation_flag=False,
                ),
                OutageCircuitMap(
                    outage_id="OTG00005",
                    circuit_id="CKT981",
                    transformer_id="TRF2796",
                    affected_count=294,
                ),
                ServicePoint(service_point_id="SP00004", circuit_id="CKT241", transformer_id="TRF9348"),
                ServicePoint(service_point_id="SP00005", circuit_id="CKT981", transformer_id="TRF2796"),
                ServicePoint(service_point_id="SP00006", circuit_id="CKT796", transformer_id="TRF7916"),
                ServicePoint(service_point_id="SP00010", circuit_id="CKT400", transformer_id="TRF8123"),
                Customer(
                    customer_id="CUST00001",
                    account_number="ACC000001",
                    first_name="James",
                    last_name="Smith",
                    is_active=True,
                ),
                Customer(
                    customer_id="CUST00005",
                    account_number="ACC000005",
                    first_name="Robert",
                    last_name="Jones",
                    is_active=True,
                ),
                Customer(
                    customer_id="CUST00008",
                    account_number="ACC000008",
                    first_name="Karen",
                    last_name="Davis",
                    is_active=True,
                ),
                Customer(
                    customer_id="CUST00015",
                    account_number="ACC000015",
                    first_name="Thomas",
                    last_name="White",
                    is_active=True,
                ),
                CustomerServicePoint(
                    customer_id="CUST00001",
                    service_point_id="SP00010",
                    customer_type_id="CT003",
                    channel_id="CH001",
                    is_medical_baseline=False,
                ),
                CustomerServicePoint(
                    customer_id="CUST00005",
                    service_point_id="SP00006",
                    customer_type_id="CT004",
                    channel_id="CH001",
                    is_medical_baseline=False,
                ),
                CustomerServicePoint(
                    customer_id="CUST00008",
                    service_point_id="SP00004",
                    customer_type_id="CT002",
                    channel_id="CH001",
                    is_medical_baseline=True,
                ),
                CustomerServicePoint(
                    customer_id="CUST00015",
                    service_point_id="SP00005",
                    customer_type_id="CT004",
                    channel_id="CH001",
                    is_medical_baseline=False,
                ),
                OutageCustomerMap(outage_id="OTG00005", customer_id="CUST00001", notification_flag=True, restored_flag=False),
                OutageCustomerMap(outage_id="OTG00005", customer_id="CUST00005", notification_flag=True, restored_flag=True),
                OutageCustomerMap(outage_id="OTG00005", customer_id="CUST00008", notification_flag=False, restored_flag=False),
            ]
        )
        db.commit()

        customers = OutageRepository(db).get_affected_customers("OTG00005")

    assert [customer["customer_id"] for customer in customers] == ["CUST00008", "CUST00001", "CUST00005"]
