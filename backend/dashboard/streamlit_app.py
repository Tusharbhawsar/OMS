import os

import pandas as pd
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.set_page_config(page_title="Outage Dashboard", page_icon="⚡", layout="wide")
st.title("Outage Communication - Phase 1 Dashboard")


def api_get(path: str):
    response = requests.get(f"{API_BASE_URL}{path}", timeout=10)
    response.raise_for_status()
    return response.json()["data"]


try:
    summary = api_get("/dashboard/summary")
    active = api_get("/dashboard/active-outages")
    notifications = api_get("/notifications?limit=100")
except Exception as exc:  # noqa: BLE001
    st.error(f"Unable to load dashboard data: {exc}")
    st.stop()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Active Outages", summary["active_outages"])
col2.metric("Affected Customers", summary["affected_customers"])
col3.metric("Medical Baseline Pending", summary["medical_baseline_pending"])
col4.metric("Delivery Rate", f"{summary['delivery_rate_percent']}%")

st.subheader("Active Outages")
st.dataframe(pd.DataFrame(active), use_container_width=True)

st.subheader("Recent Notifications")
st.dataframe(pd.DataFrame(notifications), use_container_width=True)
