"""CPA command implementation."""

from __future__ import annotations

import argparse

from ...core.upload.cpa_upload import batch_upload_to_cpa, test_cpa_connection
from ...database.session import get_db
from ..account_selection import add_account_selection_arguments, resolve_explicit_account_ids, select_accounts
from ..bootstrap import bootstrap_cli
from ..common import emit_output
from ..cpa import resolve_cpa_target, validate_cpa_target


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("cpa", help="CPA upload utilities")
    cpa_subparsers = parser.add_subparsers(dest="cpa_command", required=True)

    upload_parser = cpa_subparsers.add_parser("upload", help="upload accounts to CPA")
    upload_parser.add_argument("--database-url", help="override the database URL for this run")
    add_account_selection_arguments(upload_parser, include_proxy=False)
    upload_parser.add_argument("--only-not-uploaded", action="store_true", help="when using --all, upload only accounts not marked as uploaded")
    upload_parser.add_argument("--cpa-api-url", help="CPA API URL override")
    upload_parser.add_argument("--cpa-api-token", help="CPA API token override")
    upload_parser.add_argument("--cpa-service-id", type=int, help="database CPA service id")
    upload_parser.add_argument("--output", choices=("text", "json"), default="text")
    upload_parser.set_defaults(handler=run_cpa_upload_command)

    test_parser = cpa_subparsers.add_parser("test", help="test CPA connectivity")
    test_parser.add_argument("--database-url", help="override the database URL for this run")
    test_parser.add_argument("--cpa-api-url", help="CPA API URL override")
    test_parser.add_argument("--cpa-api-token", help="CPA API token override")
    test_parser.add_argument("--cpa-service-id", type=int, help="database CPA service id")
    test_parser.add_argument("--output", choices=("text", "json"), default="text")
    test_parser.set_defaults(handler=run_cpa_test_command)


def _print_cpa_upload_result(payload: dict) -> None:
    summary = payload["summary"]
    print(f"selected: {summary['selected_count']}")
    print(f"uploaded: {summary['success_count']}")
    print(f"failed: {summary['failed_count']}")
    print(f"skipped: {summary['skipped_count']}")

    for item in payload["details"]:
        message = item.get("message") or item.get("error") or ""
        print(f"#{item['id']} success={item['success']} email={item['email'] or '-'} {message}")


def _print_cpa_test_result(payload: dict) -> None:
    print(f"success: {payload['success']}")
    print(f"message: {payload['message']}")
    print(f"source: {payload['source']}")


def run_cpa_upload_command(args: argparse.Namespace) -> int:
    settings = bootstrap_cli(database_url=args.database_url, log_level=None)
    explicit_ids = resolve_explicit_account_ids(args.account_ids, args.account_ids_csv)

    with get_db() as db:
        selected_accounts = select_accounts(
            db,
            explicit_ids=explicit_ids,
            all_accounts=args.all,
            status=args.status,
            search=args.search,
            limit=args.limit,
            only_not_uploaded=args.only_not_uploaded,
        )
        target = resolve_cpa_target(
            db,
            settings,
            api_url=args.cpa_api_url,
            api_token=args.cpa_api_token,
            service_id=args.cpa_service_id,
        )

    validate_cpa_target(target)
    account_ids = [account.id for account in selected_accounts]
    result = batch_upload_to_cpa(account_ids, api_url=target.api_url, api_token=target.api_token)

    payload = {
        "summary": {
            "selected_count": len(account_ids),
            "success_count": result["success_count"],
            "failed_count": result["failed_count"],
            "skipped_count": result["skipped_count"],
        },
        "details": result["details"],
        "cpa_target": {
            "source": target.source,
            "service_id": target.service_id,
            "service_name": target.name,
            "api_url": target.api_url,
        },
    }
    emit_output(payload, args.output, _print_cpa_upload_result)
    return 0 if result["failed_count"] == 0 else 1


def run_cpa_test_command(args: argparse.Namespace) -> int:
    settings = bootstrap_cli(database_url=args.database_url, log_level=None)
    with get_db() as db:
        target = resolve_cpa_target(
            db,
            settings,
            api_url=args.cpa_api_url,
            api_token=args.cpa_api_token,
            service_id=args.cpa_service_id,
        )

    validate_cpa_target(target)
    success, message = test_cpa_connection(target.api_url, target.api_token)
    payload = {
        "success": success,
        "message": message,
        "source": target.source,
        "service_id": target.service_id,
        "service_name": target.name,
        "api_url": target.api_url,
    }
    emit_output(payload, args.output, _print_cpa_test_result)
    return 0 if success else 1
