"""Generate a full multi-sheet outage workbook covering many test scenarios.

Output: backend/sample_data/_outage_scenarios.xlsx
Mirrors the sheet/column layout the FileIngestionService expects.
"""
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "sample_data" / "outage_scenarios.xlsx"

# ---------------------------------------------------------------- reference
customer_type = pd.DataFrame([
    ["CT_001", "Residential", 2, "Standard residential customer"],
    ["CT_002", "Agriculture", 3, "Farm / irrigation customer"],
    ["CT_003", "Medical",     1, "Medical baseline / life support"],
    ["CT_004", "Commercial",  4, "Small business / commercial"],
    ["CT_005", "Industrial",  5, "Large industrial load"],
], columns=["customer_type_id", "type_name", "priority", "description"])

channel_master = pd.DataFrame([
    ["CH_001", "Email",    "Email notification channel", True],
    ["CH_002", "SMS",      "SMS notification channel",   True],
    ["CH_003", "Voice",    "Automated voice call",       True],
    ["CH_004", "WhatsApp", "WhatsApp (disabled)",        False],
], columns=["channel_id", "channel_name", "description", "is_active"])

# ---------------------------------------------------------------- customers
customer = pd.DataFrame([
    ["CUST_001", "ACC_001", "Ritik",  "Sharma",    "tusharbhawsar83@gmail.com", "(555) 100-0001", True],
    ["CUST_002", "ACC_002", "Tushar", "Verma",     "tusharbhawsar87@gmail.com", "(555) 100-0002", True],
    ["CUST_003", "ACC_003", "Anita",  "Mehta",     "tusharbhawsar13@gmail.com", "(555) 100-0003", True],
    ["CUST_004", "ACC_004", "Rahul",  "Singh",     "rahul@example.com",         "(555) 100-0004", True],
    ["CUST_005", "ACC_005", "Priya",  "Nair",      "priya@example.com",         "(555) 100-0005", True],
    ["CUST_006", "ACC_006", "Vikram", "Rao",       "vikram@example.com",        "(555) 100-0006", True],
    ["CUST_007", "ACC_007", "Sneha",  "Gupta",     "sneha@example.com",         "(555) 100-0007", True],
    ["CUST_008", "ACC_008", "Arjun",  "Das",       "arjun@example.com",         "(555) 100-0008", False],
    ["CUST_009", "ACC_009", "Meera",  "Iyer",      "meera@example.com",         "(555) 100-0009", True],
    ["CUST_010", "ACC_010", "Karan",  "Malhotra",  "karan@example.com",         "(555) 100-0010", True],
    ["CUST_011", "ACC_011", "Divya",  "Pillai",    "divya@example.com",         "(555) 100-0011", True],
    ["CUST_012", "ACC_012", "Sameer", "Khan",      "sameer@example.com",        "(555) 100-0012", True],
], columns=["customer_id", "account_number", "first_name", "last_name", "email", "phone", "is_active"])
customer["created_at"] = "2026-05-29 09:00:00"

# ------------------------------------------------------------ service points
regions = ["North", "South", "East", "West", "Central", "Coastal"]
service_point = pd.DataFrame([
    ["SP_001", "CKT_001", "TRF_001", "North",   35.071400, -120.941400],
    ["SP_002", "CKT_001", "TRF_001", "North",   35.071410, -120.941410],
    ["SP_003", "CKT_002", "TRF_002", "South",   35.071420, -120.941420],
    ["SP_004", "CKT_002", "TRF_002", "South",   35.071430, -120.941430],
    ["SP_005", "CKT_003", "TRF_003", "East",    35.071440, -120.941440],
    ["SP_006", "CKT_003", "TRF_003", "East",    35.071450, -120.941450],
    ["SP_007", "CKT_004", "TRF_004", "West",    35.071460, -120.941460],
    ["SP_008", "CKT_004", "TRF_004", "West",    35.071470, -120.941470],
    ["SP_009", "CKT_005", "TRF_005", "Central", 35.071480, -120.941480],
    ["SP_010", "CKT_005", "TRF_005", "Central", 35.071490, -120.941490],
    ["SP_011", "CKT_006", "TRF_006", "Coastal", 35.071500, -120.941500],
    ["SP_012", "CKT_006", "TRF_006", "Coastal", 35.071510, -120.941510],
], columns=["service_point_id", "circuit_id", "transformer_id", "geographic_region", "latitude", "longitude"])

# ------------------------------------------------- customer <-> service point
# (customer_id, service_point_id, customer_type_id, channel_id, is_medical_baseline)
csp = pd.DataFrame([
    ["CUST_001", "SP_001", "CT_001", "CH_001", False],
    ["CUST_002", "SP_002", "CT_004", "CH_002", False],
    ["CUST_003", "SP_003", "CT_003", "CH_001", True],   # medical
    ["CUST_004", "SP_004", "CT_001", "CH_002", False],
    ["CUST_005", "SP_005", "CT_003", "CH_001", True],   # medical
    ["CUST_006", "SP_006", "CT_002", "CH_003", False],
    ["CUST_007", "SP_007", "CT_001", "CH_001", False],
    ["CUST_008", "SP_008", "CT_005", "CH_002", False],
    ["CUST_009", "SP_009", "CT_003", "CH_001", True],   # medical
    ["CUST_010", "SP_010", "CT_004", "CH_002", False],
    ["CUST_011", "SP_011", "CT_001", "CH_001", False],
    ["CUST_012", "SP_012", "CT_002", "CH_003", False],
], columns=["customer_id", "service_point_id", "customer_type_id", "channel_id", "is_medical_baseline"])
csp["linked_at"] = "2026-05-29 09:10:00"

# ------------------------------------------------------------- outage events
N = None
outage_event = pd.DataFrame([
    # id, type, status, start, est_end, actual_end, etr_ml, cancel_flag, created
    ["OTG_001", "Planned",   "Active",    "2026-06-05 08:00:00", "2026-06-05 12:00:00", N,                     False, False, "2026-06-01 09:00:00"],
    ["OTG_002", "Unplanned", "Active",    "2026-06-05 06:30:00", "2026-06-05 11:30:00", N,                     True,  False, "2026-06-05 06:35:00"],
    ["OTG_003", "Planned",   "Scheduled", "2026-06-06 09:00:00", "2026-06-06 13:00:00", N,                     False, False, "2026-06-02 10:00:00"],
    ["OTG_004", "Planned",   "Scheduled", "2026-06-10 14:00:00", "2026-06-10 18:00:00", N,                     False, False, "2026-06-03 10:00:00"],
    ["OTG_005", "Planned",   "Scheduled", "2026-06-20 10:00:00", "2026-06-20 16:00:00", N,                     True,  False, "2026-06-04 10:00:00"],
    ["OTG_006", "Planned",   "Scheduled", "2026-06-08 11:00:00", N,                     N,                     False, False, "2026-06-04 11:00:00"],
    ["OTG_007", "Unplanned", "Active",    "2026-06-05 07:15:00", "2026-06-05 10:00:00", N,                     False, False, "2026-06-05 07:20:00"],
    ["OTG_008", "Planned",   "Cancelled", "2026-06-07 09:00:00", "2026-06-07 12:00:00", N,                     False, True,  "2026-06-02 09:00:00"],
    ["OTG_009", "Planned",   "Scheduled", "2026-06-12 08:00:00", "2026-06-12 12:00:00", N,                     False, True,  "2026-06-03 08:00:00"],
    ["OTG_010", "Planned",   "Completed", "2026-06-01 09:00:00", "2026-06-01 13:00:00", "2026-06-01 12:45:00", False, False, "2026-05-28 09:00:00"],
    ["OTG_011", "Unplanned", "Restored",  "2026-06-02 22:00:00", "2026-06-03 02:00:00", "2026-06-03 01:30:00", True,  False, "2026-06-02 22:05:00"],
    ["OTG_012", "Planned",   "Resolved",  "2026-05-30 10:00:00", "2026-05-30 14:00:00", "2026-05-30 14:10:00", False, False, "2026-05-25 10:00:00"],
], columns=["outage_id", "outage_type", "status", "start_time", "estimated_end_time", "actual_end_time", "etr_predicted_by_ml", "cancellation_flag", "created_at"])

# --------------------------------------------------------- outage <-> circuit
circuit_of = {
    "OTG_001": ("CKT_001", "TRF_001"), "OTG_002": ("CKT_002", "TRF_002"),
    "OTG_003": ("CKT_003", "TRF_003"), "OTG_004": ("CKT_004", "TRF_004"),
    "OTG_005": ("CKT_005", "TRF_005"), "OTG_006": ("CKT_006", "TRF_006"),
    "OTG_007": ("CKT_001", "TRF_001"), "OTG_008": ("CKT_002", "TRF_002"),
    "OTG_009": ("CKT_003", "TRF_003"), "OTG_010": ("CKT_004", "TRF_004"),
    "OTG_011": ("CKT_005", "TRF_005"), "OTG_012": ("CKT_006", "TRF_006"),
}
ocm_rows = []
for oid, (ckt, trf) in circuit_of.items():
    ocm_rows.append([oid, ckt, trf, 2, "2026-06-01 09:15:00"])
outage_circuit_map = pd.DataFrame(ocm_rows, columns=["outage_id", "circuit_id", "transformer_id", "affected_count", "linked_at"])

# -------------------------------------------------------- outage <-> customer
# (outage_id, customer_id, notification_flag, restored_flag)
outage_customer_map = pd.DataFrame([
    ["OTG_001", "CUST_001", False, False],
    ["OTG_001", "CUST_002", True,  False],
    ["OTG_002", "CUST_003", False, False],   # Active + medical + not notified -> medical pending
    ["OTG_002", "CUST_004", False, False],
    ["OTG_003", "CUST_005", False, False],   # Scheduled + medical + not notified -> medical pending
    ["OTG_003", "CUST_006", True,  False],
    ["OTG_004", "CUST_007", False, False],
    ["OTG_004", "CUST_008", False, False],
    ["OTG_005", "CUST_009", False, False],   # Scheduled + medical + not notified -> medical pending
    ["OTG_005", "CUST_010", True,  False],
    ["OTG_006", "CUST_011", False, False],
    ["OTG_006", "CUST_012", False, False],
    ["OTG_007", "CUST_001", False, False],   # same customer in 2nd active outage (distinct-count test)
    ["OTG_007", "CUST_002", False, False],
    ["OTG_008", "CUST_003", False, False],   # Cancelled -> excluded from affected count
    ["OTG_008", "CUST_004", False, False],
    ["OTG_009", "CUST_005", False, False],   # Scheduled (flag set) + medical -> still counts
    ["OTG_009", "CUST_006", False, False],
    ["OTG_010", "CUST_007", True,  True],    # Completed
    ["OTG_011", "CUST_009", True,  True],    # Restored
    ["OTG_012", "CUST_011", True,  True],    # Resolved
], columns=["outage_id", "customer_id", "notification_flag", "restored_flag"])

# ----------------------------------------------------------- notifications
notification = pd.DataFrame([
    ["NOTIF_001", "OTG_001", "CUST_001", "Advance Notice", "CH_001", "Delivered", "2026-06-04 09:00:00", "2026-06-04 09:00:05", "Planned outage OTG_001 starts 06-05 08:00."],
    ["NOTIF_002", "OTG_001", "CUST_002", "Advance Notice", "CH_002", "Delivered", "2026-06-04 09:00:00", "2026-06-04 09:00:06", "Planned outage OTG_001 starts 06-05 08:00."],
    ["NOTIF_003", "OTG_002", "CUST_003", "Outage Alert",   "CH_001", "Failed",    "2026-06-05 06:40:00", N,                     "Unplanned outage OTG_002 in your area."],
    ["NOTIF_004", "OTG_003", "CUST_005", "Advance Notice", "CH_001", "Pending",   N,                     N,                     "Planned outage OTG_003 starts 06-06 09:00."],
    ["NOTIF_005", "OTG_003", "CUST_006", "Advance Notice", "CH_003", "Sent",      "2026-06-05 10:00:00", N,                     "Planned outage OTG_003 starts 06-06 09:00."],
    ["NOTIF_006", "OTG_010", "CUST_007", "Restoration",    "CH_002", "Delivered", "2026-06-01 12:50:00", "2026-06-01 12:50:04", "Power restored for outage OTG_010."],
    ["NOTIF_007", "OTG_011", "CUST_009", "Restoration",    "CH_001", "Delivered", "2026-06-03 01:35:00", "2026-06-03 01:35:03", "Power restored for outage OTG_011."],
    ["NOTIF_008", "OTG_002", "CUST_004", "Outage Alert",   "CH_002", "Failed",    "2026-06-05 06:41:00", N,                     "Unplanned outage OTG_002 in your area."],
], columns=["notification_id", "outage_id", "customer_id", "notification_type", "channel_id", "status", "sent_at", "delivered_at", "message_content"])

sheets = {
    "CUSTOMER_TYPE": customer_type,
    "CHANNEL_MASTER": channel_master,
    "CUSTOMER": customer,
    "SERVICE_POINT": service_point,
    "OUTAGE_EVENT": outage_event,
    "CUSTOMER_SERVICE_POINT": csp,
    "OUTAGE_CIRCUIT_MAP": outage_circuit_map,
    "OUTAGE_CUSTOMER_MAP": outage_customer_map,
    "NOTIFICATION": notification,
}

OUT.parent.mkdir(parents=True, exist_ok=True)
with pd.ExcelWriter(OUT, engine="openpyxl") as writer:
    for name, df in sheets.items():
        df.to_excel(writer, sheet_name=name, index=False)

print(f"Wrote {OUT}")
for name, df in sheets.items():
    print(f"  {name:24s} {len(df)} rows")
