"""Core SQLAlchemy metadata and column helpers."""

from collections.abc import Callable
from datetime import datetime

from cortex_common.clock import utc_now
from sqlalchemy import DateTime, MetaData, Text, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base declarative model for Cortex persistence."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def created_at_column() -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )


def updated_at_column() -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )


def nullable_timestamp_column() -> Mapped[datetime | None]:
    return mapped_column(DateTime(timezone=True), nullable=True)


def json_text_column(default: str = "{}") -> Mapped[str]:
    return mapped_column(
        Text,
        nullable=False,
        default=lambda: default,
        server_default=text(f"'{default}'"),
    )


def text_default(value: str) -> Callable[[], str]:
    return lambda: value
