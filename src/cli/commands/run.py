"""Primary config-driven workflow command."""

from __future__ import annotations

import argparse

from ..common import emit_output, positive_int
from .accounts import _print_ensure_target_result, execute_ensure_target


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("run", help="run the full workflow using config.json defaults")
    parser.add_argument("--target-count", type=positive_int, help="temporary override for config.workflow.target_account_count")
    parser.add_argument(
        "--refresh-before-validate",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="temporarily override config.workflow.refresh_before_validate",
    )
    parser.add_argument(
        "--sync-cpa",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="temporarily override config.workflow.auto_sync_cpa",
    )
    parser.add_argument("--output", choices=("text", "json"), default="text", help="final result format")

    parser.add_argument("--database-url", help=argparse.SUPPRESS)
    parser.add_argument("--log-level", help=argparse.SUPPRESS)
    parser.add_argument("--proxy", help=argparse.SUPPRESS)
    parser.add_argument("--proxy-id", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--service-type", help=argparse.SUPPRESS)
    parser.add_argument("--service-id", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--service-config", help=argparse.SUPPRESS)
    parser.add_argument("--service-config-file", help=argparse.SUPPRESS)
    parser.add_argument("--max-attempts", type=positive_int, help=argparse.SUPPRESS)
    parser.add_argument("--cpa-api-url", help=argparse.SUPPRESS)
    parser.add_argument("--cpa-api-token", help=argparse.SUPPRESS)
    parser.add_argument("--cpa-service-id", type=int, help=argparse.SUPPRESS)
    parser.add_argument(
        "--delete-invalid-accounts",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.set_defaults(handler=run_workflow_command)


def run_workflow_command(args: argparse.Namespace) -> int:
    payload, exit_code = execute_ensure_target(args)
    emit_output(payload, args.output, _print_ensure_target_result)
    return exit_code
