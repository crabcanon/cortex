"""ID generation helpers."""

from uuid import uuid4


def new_prefixed_id(prefix: str) -> str:
    """Generate a stable prefixed identifier."""
    normalized_prefix = prefix.strip().lower().replace(" ", "_")
    return f"{normalized_prefix}_{uuid4().hex[:24]}"
