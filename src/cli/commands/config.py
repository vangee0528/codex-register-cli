"""Config command implementation."""

from __future__ import annotations

import argparse

from ...config import get_config_path, read_raw_config
from ..bootstrap import bootstrap_cli
from ..common import emit_output
from ..config_ui import run_config_ui


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("config", help="manage config.json and launch the settings UI")
    config_subparsers = parser.add_subparsers(dest="config_command", required=True)

    show_parser = config_subparsers.add_parser("show", help="print the current config.json")
    show_parser.add_argument("--output", choices=("text", "json"), default="json")
    show_parser.set_defaults(handler=run_config_show_command)

    path_parser = config_subparsers.add_parser("path", help="print the active config.json path")
    path_parser.set_defaults(handler=run_config_path_command)

    ui_parser = config_subparsers.add_parser("ui", help="launch the local config editor UI")
    ui_parser.add_argument("--host", help="host to bind the local UI server")
    ui_parser.add_argument("--port", type=int, help="port to bind the local UI server")
    ui_parser.set_defaults(handler=run_config_ui_command)


def run_config_show_command(args: argparse.Namespace) -> int:
    bootstrap_cli(database_url=None, log_level=None)
    emit_output(read_raw_config(), args.output)
    return 0


def run_config_path_command(args: argparse.Namespace) -> int:
    bootstrap_cli(database_url=None, log_level=None)
    print(get_config_path())
    return 0


def run_config_ui_command(args: argparse.Namespace) -> int:
    settings = bootstrap_cli(database_url=None, log_level=None)
    host = args.host or settings.config_ui_host
    port = args.port or settings.config_ui_port
    run_config_ui(host, port)
    return 0
