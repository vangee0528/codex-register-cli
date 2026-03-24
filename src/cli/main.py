"""Main CLI entrypoint."""

from __future__ import annotations

import argparse
import sys

from .commands import accounts, config, cpa, database, register, run, services
from .commands.accounts import (
    run_delete_invalid_accounts_command,
    run_ensure_target_accounts_command,
    run_list_accounts_command,
    run_validate_accounts_command,
)
from .commands.config import run_config_path_command, run_config_show_command, run_config_ui_command
from .commands.cpa import run_cpa_sync_local_command, run_cpa_test_command, run_cpa_upload_command
from .commands.database import run_db_init_command
from .commands.register import run_register_command
from .commands.run import run_workflow_command
from .commands.services import run_list_proxies_command, run_list_services_command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex-console",
        description="Command-line registration workflow for codex-console.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run.add_parser(subparsers)
    register.add_parser(subparsers)
    accounts.add_parser(subparsers)
    cpa.add_parser(subparsers)
    config.add_parser(subparsers)
    services.add_parser(subparsers)
    database.add_parser(subparsers)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return args.handler(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


__all__ = [
    "build_parser",
    "main",
    "run_workflow_command",
    "run_register_command",
    "run_list_services_command",
    "run_list_proxies_command",
    "run_db_init_command",
    "run_list_accounts_command",
    "run_validate_accounts_command",
    "run_delete_invalid_accounts_command",
    "run_ensure_target_accounts_command",
    "run_cpa_upload_command",
    "run_cpa_test_command",
    "run_cpa_sync_local_command",
    "run_config_show_command",
    "run_config_path_command",
    "run_config_ui_command",
]
