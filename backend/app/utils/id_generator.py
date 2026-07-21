from uuid import uuid4

from app.utils.time import ist_now


def generate_prefixed_id(prefix: str, max_length: int = 30) -> str:
    """Generate a compact unique identifier with a domain prefix."""
    timestamp = ist_now().strftime("%y%m%d%H%M%S")
    random_part = uuid4().hex[:8].upper()
    return f"{prefix}{timestamp}{random_part}"[:max_length]
