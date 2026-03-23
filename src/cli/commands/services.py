"""Services command implementation."""

from __future__ import annotations

import argparse

from ...database.session import get_db
from ..bootstrap import bootstrap_cli
from ..common import print_collection
from ..registration import list_available_proxies, list_available_services


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("services", help="inspect configured resources")
    service_subparsers = parser.add_subparsers(dest="services_command", required=True)

    list_services_parser = service_subparsers.add_parser("list", help="list email services")
    list_services_parser.add_argument("--database-url", help="override the database URL for this run")
    list_services_parser.add_argument("--output", choices=("text", "json"), default="text", help="output format")
    list_services_parser.set_defaults(handler=run_list_services_command)

    list_proxies_parser = service_subparsers.add_parser("proxies", help="list proxies")
    list_proxies_parser.add_argument("--database-url", help="override the database URL for this run")
    list_proxies_parser.add_argument("--output", choices=("text", "json"), default="text", help="output format")
    list_proxies_parser.set_defaults(handler=run_list_proxies_command)


def run_list_services_command(args: argparse.Namespace) -> int:
    settings = bootstrap_cli(database_url=args.database_url, log_level=None)
    with get_db() as db:
        items = list_available_services(db, settings)
    print_collection(items, args.output)
    return 0


def run_list_proxies_command(args: argparse.Namespace) -> int:
    settings = bootstrap_cli(database_url=args.database_url, log_level=None)
    with get_db() as db:
        items = list_available_proxies(db, settings)
    print_collection(items, args.output)
    return 0
