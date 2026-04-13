"""Pagination DTOs."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationRequest(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=500)


class PaginationEnvelope(BaseModel, Generic[T]):
    items: list[T]
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1)
    total: int = Field(default=0, ge=0)
