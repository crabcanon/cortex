"""Idempotency helpers."""

from hashlib import sha256

from .exceptions import ValidationError


def normalize_idempotency_key(value: str) -> str:
    """Normalize or derive an idempotency key."""
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError("idempotency key cannot be empty")
    if len(cleaned) <= 96:
        return cleaned
    return sha256(cleaned.encode("utf-8")).hexdigest()
