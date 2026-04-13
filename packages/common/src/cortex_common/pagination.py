"""Pagination helpers."""

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class PaginationWindow:
    """Normalized pagination window."""

    offset: int = 0
    limit: int = 50

    @classmethod
    def from_params(cls, offset: int | None = None, limit: int | None = None) -> "PaginationWindow":
        raw_offset = max(offset or 0, 0)
        raw_limit = min(max(limit or 50, 1), 500)
        return cls(offset=raw_offset, limit=raw_limit)
