"""Database command implementation."""

from __future__ import annotations

import argparse

from ..bootstrap import bootstrap_cli


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("db", help="database utilities")
    db_subparsers = parser.add_subparsers(dest="db_command", required=True)

    init_parser = db_subparsers.add_parser("init", help="initialize database and default settings")
    init_parser.add_argument("--database-url", help="override the database URL for this run")
    init_parser.add_argument("--log-level", help="override configured log level")
    init_parser.set_defaults(handler=run_db_init_command)


def run_db_init_command(args: argparse.Namespace) -> int:
    bootstrap_cli(database_url=args.database_url, log_level=args.log_level)
    print("Database initialized")
    return 0
