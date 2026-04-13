"""Alembic command wrapper for Cortex."""

from argparse import ArgumentParser
from collections.abc import Sequence
from pathlib import Path

from alembic import command
from alembic.config import Config
from cortex_common import load_settings

from .engine import normalize_alembic_dsn


def build_alembic_config(db_url: str | None = None) -> Config:
    """Create an Alembic config rooted at the db package."""
    package_root = Path(__file__).resolve().parents[2]
    config = Config(str(package_root / "alembic.ini"))
    config.set_main_option("script_location", str(package_root / "migrations"))
    config.set_main_option(
        "sqlalchemy.url",
        db_url or normalize_alembic_dsn(load_settings().database.dsn),
    )
    return config


def main(argv: Sequence[str] | None = None) -> int:
    parser = ArgumentParser(prog="cortex-db-migrate")
    parser.add_argument("command", choices=["upgrade", "downgrade", "current"])
    parser.add_argument("target", nargs="?", default="head")
    parser.add_argument("--db-url", dest="db_url")
    args = parser.parse_args(argv)

    config = build_alembic_config(args.db_url)

    if args.command == "upgrade":
        command.upgrade(config, args.target)
    elif args.command == "downgrade":
        command.downgrade(config, args.target)
    else:
        command.current(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
