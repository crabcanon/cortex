"""Focused unit tests for DB path preparation helpers."""

from __future__ import annotations

import time
from pathlib import Path

from cortex_db.cli import build_alembic_config
from cortex_db.engine import create_database_engine, ensure_sqlite_database_path


def _case_dir(name: str) -> Path:
    root = Path("runtime-test-data")
    root.mkdir(parents=True, exist_ok=True)
    case_dir = root / f"{name}-{time.time_ns()}"
    case_dir.mkdir(parents=True, exist_ok=True)
    return case_dir


def test_ensure_sqlite_database_path_creates_parent_directory() -> None:
    case_dir = _case_dir("unit-db-path-helper")
    db_path = case_dir / "nested" / "cortex.db"

    ensure_sqlite_database_path(f"sqlite+aiosqlite:///{db_path.as_posix()}")

    assert db_path.parent.exists()


def test_build_alembic_config_creates_relative_sqlite_parent_directory() -> None:
    case_dir = _case_dir("unit-db-alembic-path")
    relative_path = case_dir / "db-root" / "cortex.db"
    relative_dsn = f"sqlite:///{relative_path.as_posix()}"

    config = build_alembic_config(relative_dsn)

    assert config.get_main_option("sqlalchemy.url") == relative_dsn
    assert relative_path.parent.exists()


def test_create_database_engine_prepares_sqlite_path_before_engine_use() -> None:
    case_dir = _case_dir("unit-db-engine-path")
    db_path = case_dir / "engine-root" / "cortex.db"

    engine = create_database_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")

    try:
        assert db_path.parent.exists()
    finally:
        import asyncio

        asyncio.run(engine.dispose())
