"""End-to-end run: load the comprehensive workbook, notify ALL customers across ALL
channels (one notification per outage), then query Twilio for the REAL delivery status
of each SMS/WhatsApp/IVR message (not just the accepted status)."""
import sys
import time
sys.path.insert(0, "backend")

import requests
from sqlalchemy import text
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.file_ingestion_service import FileIngestionService
from app.services.planned_outage_service import PlannedOutageService

WB = r"C:\mleu\outage_poc_LLm_intergration_jun26\backend\sample_data\outage_data_for_twilio.xlsx"
s = get_settings()
SID, TOK = s.twilio_account_sid.strip(), s.twilio_auth_token.strip()
CA = "backend/corp_ca_bundle.pem"

# One notification per outage -> covers all 8 customers across all channels.
PLAN = [
    ("OTG_001", "Advance Notice"),   # SMS      (CUST_001)
    ("OTG_002", "Advance Notice"),   # WhatsApp (CUST_002)
    ("OTG_003", "Advance Notice"),   # IVR      (CUST_003)
    ("OTG_004", "Advance Notice"),   # Email    (CUST_004)
    ("OTG_005", "Cancellation Alert"),  # SMS cancellation (CUST_005)
    ("OTG_006", "Advance Notice"),   # IVR+SMS+Email medical (CUST_006/007/008)
]

db = SessionLocal()

print("=== STEP 1: LOAD WORKBOOK (reset) ===")
with open(WB, "rb") as fh:
    res = FileIngestionService(db, reset_on_upload=True).import_upload("outage_data_for_twilio.xlsx", fh.read())
print("  imported:", res["imported_tables"])

print("\n=== STEP 2: NOTIFY ALL CUSTOMERS ===")
svc = PlannedOutageService(db)
for outage_id, stage in PLAN:
    r = svc.process_outage(outage_id, stage)
    print(f"  {outage_id} [{stage:16}] created={r.get('notifications_created')} "
          f"delivered={r.get('notifications_delivered')} failed={r.get('notifications_failed')}")

print("\n  (waiting ~12s for Twilio async delivery status to settle...)")
time.sleep(12)

print("\n=== STEP 3: REAL DELIVERY STATUS PER CUSTOMER/CHANNEL ===")
rows = db.execute(text(
    "SELECT n.customer_id, n.outage_id, n.channel_id, na.provider_name, na.status, na.provider_message_id "
    "FROM notification n JOIN notification_attempt na ON na.notification_id = n.notification_id "
    "ORDER BY n.customer_id"
)).fetchall()

def real_status(provider_name, msg_id):
    if not msg_id or not provider_name or not provider_name.startswith("twilio"):
        return "-"
    resource = "Calls" if provider_name == "twilio_voice" else "Messages"
    try:
        resp = requests.get(f"https://api.twilio.com/2010-04-01/Accounts/{SID}/{resource}/{msg_id}.json",
                            auth=(SID, TOK), timeout=15, verify=CA)
        d = resp.json()
        ec = d.get("error_code")
        return f"{d.get('status')}" + (f" (err {ec})" if ec else "")
    except Exception as e:  # noqa: BLE001
        return f"query-failed: {e}"

problems = []
for cust, outage, chan, prov, accepted, msg_id in rows:
    real = real_status(prov, msg_id)
    line = f"  {cust} | {chan} | {str(prov):16} | accepted={accepted:9} | REAL={real}"
    print(line)
    bad = (accepted != "Delivered") or ("failed" in str(real)) or ("undelivered" in str(real)) or ("err" in str(real))
    if bad:
        problems.append((cust, prov, real))

print("\n=== SUMMARY ===")
if not problems:
    print("  All notifications delivered to all customers. No problems.")
else:
    print(f"  {len(problems)} problem(s):")
    for c, p, r in problems:
        print(f"    - {c} via {p}: {r}")

db.close()
