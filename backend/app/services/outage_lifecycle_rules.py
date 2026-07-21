"""Shared outage lifecycle invariants.

Real outages are *living records*: an outage that is still Scheduled or Active cannot
already have an ``actual_end_time`` (that is only knowable once power is restored) and
cannot be pre-marked as cancelled (cancellation is a later event). These rules keep every
write path — bulk import, the cancel endpoint, and any future event applier / feed
simulator — agreeing on the same invariants, so the stored data always looks like it came
from a real feed instead of a snapshot that already knows the future.
"""
from datetime import datetime
from typing import Any

# Not finished yet: the outcome (end time / cancellation) is still unknown.
LIVE_STATUSES = {"scheduled", "active"}
# Genuinely over: post-fact values (actual_end_time) are legitimate on these.
RESTORED_STATUSES = {"completed", "restored", "resolved"}
CANCELLED_STATUS = "cancelled"


def normalize_status(status: Any) -> str:
    """Lower/strip a status value for case-insensitive comparison."""
    return str(status or "").strip().lower()


def is_live_status(status: Any) -> bool:
    """True when the outage has not finished yet (Scheduled or Active)."""
    return normalize_status(status) in LIVE_STATUSES


def normalize_imported_outage(record: dict[str, Any]) -> dict[str, Any]:
    """Strip "future knowledge" from an outage row at import time (Option 2 guard).

    For a still-live outage (Scheduled/Active):
      - ``actual_end_time`` is forced to None (it cannot have ended yet), and
      - ``cancellation_flag`` is forced to False (cancellation must arrive as an event).

    Genuine historical rows (Completed/Restored/Resolved/Cancelled) are left untouched so
    real past data can still be seeded. Only keys already present in the record are
    modified, so the importer's upsert column set is not widened unnecessarily.
    """
    if is_live_status(record.get("status")):
        if "actual_end_time" in record:
            record["actual_end_time"] = None
        if "cancellation_flag" in record:
            record["cancellation_flag"] = False
    return record


def apply_cancellation(outage: Any, cancelled_at: datetime) -> None:
    """Apply a cancellation event to an OutageEvent (Option 3).

    Sets the cancellation flag, moves the status to Cancelled, and stamps ``cancelled_at``
    so cancellation has its own timestamp (parallel to actual_end_time for restoration).
    """
    outage.cancellation_flag = True
    outage.status = "Cancelled"
    outage.cancelled_at = cancelled_at


def apply_restoration(outage: Any, restored_at: datetime) -> None:
    """Apply a restoration event to an OutageEvent (Option 3, restoration counterpart).

    Stamps ``actual_end_time`` (the real, now-known end) and moves the status to Restored.
    This is the event that legitimately fills actual_end_time after the outage is over,
    which the importer deliberately refuses to set for a still-live outage.

    Status is "Restored" (not "Completed") on purpose: the lifecycle candidate query and
    the "Outage Restored" rule both recognise Restored/Resolved, so the restored outage
    stays in the batch's candidate set and its restoration notification actually fires.
    """
    outage.actual_end_time = restored_at
    outage.status = "Restored"
