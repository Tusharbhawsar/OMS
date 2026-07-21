from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30), "IST")


def ist_now() -> datetime:
    """Return the current wall-clock time in IST as a naive datetime.

    The whole application works in IST. We strip tzinfo so every value
    (uploaded outage times, sent_at, now) is a naive IST datetime and can be
    compared directly without any UTC<->IST conversion.
    """
    return datetime.now(IST).replace(tzinfo=None)


def ensure_ist(value: datetime | None) -> datetime | None:
    """Normalize any datetime to naive IST.

    Naive values are assumed to already be IST (that is how outage times are
    uploaded and how we store timestamps). Aware values are converted to IST
    and then made naive.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(IST).replace(tzinfo=None)


def format_ist_datetime(value: datetime | None) -> str:
    """Format a naive IST datetime for customer-facing IST messages."""
    local_value = ensure_ist(value)
    if local_value is None:
        return "to be confirmed"
    return local_value.strftime("%Y-%m-%d %H:%M")
