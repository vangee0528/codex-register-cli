"""Account management command implementation."""

from __future__ import annotations

import argparse
from types import SimpleNamespace
from typing import Any

from ...core.openai.token_refresh import refresh_account_token, validate_account_token
from ...core.upload.cpa_upload import batch_upload_to_cpa
from ...database import crud
from ...database.models import Account
from ...database.session import get_db
from ..account_selection import add_account_selection_arguments, resolve_explicit_account_ids, select_accounts
from ..bootstrap import bootstrap_cli
from ..common import emit_output, positive_int
from ..cpa import resolve_cpa_target, validate_cpa_target
from .register import SERVICE_TYPE_CHOICES, _run_single_registration


STATUS_ACTIVE = "active"
STATUS_EXPIRED = "expired"


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("accounts", help="manage stored accounts")
    account_subparsers = parser.add_subparsers(dest="accounts_command", required=True)

    list_parser = account_subparsers.add_parser("list", help="list accounts stored in the database")
    list_parser.add_argument("--database-url", help="override the database URL for this run")
    list_parser.add_argument("--status", choices=("active", "expired", "banned", "failed"))
    list_parser.add_argument("--search", help="substring match on email, account id, or workspace id")
    list_parser.add_argument("--limit", type=int, default=100)
    list_parser.add_argument("--output", choices=("text", "json"), default="text")
    list_parser.set_defaults(handler=run_list_accounts_command)

    validate_parser = account_subparsers.add_parser("validate", help="validate account availability via stored access tokens")
    validate_parser.add_argument("--database-url", help="override the database URL for this run")
    add_account_selection_arguments(validate_parser, include_proxy=True)
    validate_parser.add_argument("--refresh-before-validate", action="store_true", help="try refreshing the token before validation")
    validate_parser.add_argument("--output", choices=("text", "json"), default="text")
    validate_parser.set_defaults(handler=run_validate_accounts_command)

    delete_invalid_parser = account_subparsers.add_parser("delete-invalid", help="validate accounts and delete the invalid ones")
    delete_invalid_parser.add_argument("--database-url", help="override the database URL for this run")
    add_account_selection_arguments(delete_invalid_parser, include_proxy=True)
    delete_invalid_parser.add_argument("--refresh-before-validate", action="store_true", help="try refreshing the token before validation")
    delete_invalid_parser.add_argument("--output", choices=("text", "json"), default="text")
    delete_invalid_parser.set_defaults(handler=run_delete_invalid_accounts_command)

    ensure_parser = account_subparsers.add_parser("ensure-target", help="ensure the database contains the requested number of valid accounts")
    ensure_parser.add_argument("--database-url", help="override the database URL for this run")
    ensure_parser.add_argument("--target-count", type=positive_int, required=True, help="desired number of valid accounts after validation and refill")
    ensure_parser.add_argument("--refresh-before-validate", action="store_true", help="try refreshing stored tokens before validation")
    ensure_parser.add_argument("--proxy", help="proxy URL used for validation and registration")
    ensure_parser.add_argument("--proxy-id", type=int, help="database proxy id used for registration")
    ensure_parser.add_argument("--service-type", choices=SERVICE_TYPE_CHOICES, default="tempmail", help="email service type to use when --service-id is not provided")
    ensure_parser.add_argument("--service-id", type=int, help="database email service id; overrides --service-type")
    ensure_parser.add_argument("--service-config", help="inline JSON object merged into the resolved email service config")
    ensure_parser.add_argument("--service-config-file", help="path to a JSON file merged into the resolved email service config")
    ensure_parser.add_argument("--log-level", help="override configured log level")
    ensure_parser.add_argument("--max-attempts", type=positive_int, help="maximum registration attempts used to close the account gap")
    ensure_parser.add_argument("--skip-cpa-sync", action="store_true", help="skip the final CPA upload of all active accounts")
    ensure_parser.add_argument("--cpa-api-url", help="CPA API URL override")
    ensure_parser.add_argument("--cpa-api-token", help="CPA API token override")
    ensure_parser.add_argument("--cpa-service-id", type=int, help="database CPA service id")
    ensure_parser.add_argument("--output", choices=("text", "json"), default="text")
    ensure_parser.set_defaults(handler=run_ensure_target_accounts_command)


def _account_to_summary(account) -> dict[str, Any]:
    return {
        "id": account.id,
        "email": account.email,
        "status": account.status,
        "account_id": account.account_id,
        "workspace_id": account.workspace_id,
        "cpa_uploaded": bool(account.cpa_uploaded),
        "registered_at": account.registered_at.isoformat() if account.registered_at else None,
        "last_refresh": account.last_refresh.isoformat() if account.last_refresh else None,
        "expires_at": account.expires_at.isoformat() if account.expires_at else None,
    }


def _print_account_list(payload: list[dict[str, Any]]) -> None:
    if not payload:
        print("No records found")
        return

    for item in payload:
        print(
            f"#{item['id']} {item['email']} status={item['status']} "
            f"cpa_uploaded={item['cpa_uploaded']} workspace_id={item['workspace_id'] or '-'}"
        )


def _print_validation_result(payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    print(f"checked: {summary['checked_count']}")
    print(f"valid: {summary['valid_count']}")
    print(f"invalid: {summary['invalid_count']}")
    print(f"deleted: {summary['deleted_count']}")

    for item in payload["results"]:
        refresh_text = "not-run"
        if item["refresh"] is not None:
            refresh_text = f"{item['refresh']['success']}"
        print(
            f"#{item['id']} valid={item['valid']} deleted={item['deleted']} refresh={refresh_text} "
            f"status={item['status_after']} email={item['email']} error={item['error'] or '-'}"
        )


def _print_ensure_target_result(payload: dict[str, Any]) -> None:
    print(f"available_before_registration: {payload['available_count_before_registration']}")
    print(f"target_count: {payload['target_count']}")
    print(f"required_registrations: {payload['required_registrations']}")
    print(f"final_active_count: {payload['final_active_count']}")
    print(f"registration_attempts: {payload['registration']['attempted_count']}")
    print(f"registration_successes: {payload['registration']['success_count']}")
    print(f"registration_failures: {payload['registration']['failed_count']}")
    if payload["cpa_sync"] is not None:
        print(f"cpa_uploaded: {payload['cpa_sync']['success_count']}")
        print(f"cpa_failed: {payload['cpa_sync']['failed_count']}")
        print(f"cpa_skipped: {payload['cpa_sync']['skipped_count']}")


def run_list_accounts_command(args: argparse.Namespace) -> int:
    bootstrap_cli(database_url=args.database_url, log_level=None)
    with get_db() as db:
        items = [_account_to_summary(account) for account in crud.get_accounts(db, limit=args.limit, status=args.status, search=args.search)]
    emit_output(items, args.output, _print_account_list)
    return 0


def _load_snapshots(
    *,
    explicit_ids: list[int],
    all_accounts: bool,
    status: str | None,
    search: str | None,
    limit: int | None,
) -> list[dict[str, Any]]:
    with get_db() as db:
        selected_accounts = select_accounts(
            db,
            explicit_ids=explicit_ids,
            all_accounts=all_accounts,
            status=status,
            search=search,
            limit=limit,
        )
        return [
            {
                "id": account.id,
                "email": account.email,
                "status_before": account.status,
            }
            for account in selected_accounts
        ]


def _validate_snapshots(
    snapshots: list[dict[str, Any]],
    *,
    proxy: str | None,
    refresh_before_validate: bool,
    delete_invalid: bool,
) -> tuple[dict[str, Any], int]:
    results: list[dict[str, Any]] = []
    invalid_ids: list[int] = []

    for snapshot in snapshots:
        refresh_payload = None
        if refresh_before_validate:
            refresh_result = refresh_account_token(snapshot["id"], proxy_url=proxy)
            refresh_payload = {
                "success": refresh_result.success,
                "error": refresh_result.error_message or None,
                "expires_at": refresh_result.expires_at.isoformat() if refresh_result.expires_at else None,
            }

        valid, error = validate_account_token(snapshot["id"], proxy_url=proxy)
        status_after = STATUS_ACTIVE if valid else STATUS_EXPIRED

        with get_db() as db:
            updated = crud.update_account(db, snapshot["id"], status=status_after)
            if updated is not None:
                status_after = updated.status

        if not valid:
            invalid_ids.append(snapshot["id"])

        results.append(
            {
                "id": snapshot["id"],
                "email": snapshot["email"],
                "status_before": snapshot["status_before"],
                "status_after": status_after,
                "valid": valid,
                "error": error,
                "refresh": refresh_payload,
                "deleted": False,
            }
        )

    deleted_ids: set[int] = set()
    if delete_invalid and invalid_ids:
        with get_db() as db:
            crud.delete_accounts_batch(db, invalid_ids)

        with get_db() as db:
            remaining_ids = {
                row[0]
                for row in db.query(Account.id).filter(Account.id.in_(invalid_ids)).all()
            }
        deleted_ids = set(invalid_ids) - remaining_ids

        for item in results:
            if item["id"] in deleted_ids:
                item["deleted"] = True

    summary = {
        "checked_count": len(results),
        "valid_count": sum(1 for item in results if item["valid"]),
        "invalid_count": sum(1 for item in results if not item["valid"]),
        "deleted_count": len(deleted_ids),
    }
    payload = {
        "summary": summary,
        "results": results,
    }

    if delete_invalid:
        exit_code = 0 if summary["invalid_count"] == summary["deleted_count"] else 1
    else:
        exit_code = 0 if summary["invalid_count"] == 0 else 1

    return payload, exit_code


def _run_validation(args: argparse.Namespace, *, delete_invalid: bool) -> tuple[dict[str, Any], int]:
    bootstrap_cli(database_url=args.database_url, log_level=None)
    explicit_ids = resolve_explicit_account_ids(args.account_ids, args.account_ids_csv)
    snapshots = _load_snapshots(
        explicit_ids=explicit_ids,
        all_accounts=args.all,
        status=args.status,
        search=args.search,
        limit=args.limit,
    )
    return _validate_snapshots(
        snapshots,
        proxy=args.proxy,
        refresh_before_validate=args.refresh_before_validate,
        delete_invalid=delete_invalid,
    )


def _get_active_account_ids() -> list[int]:
    with get_db() as db:
        return [row[0] for row in db.query(Account.id).filter(Account.status == STATUS_ACTIVE).order_by(Account.id.asc()).all()]


def _default_max_attempts(required_registrations: int) -> int:
    if required_registrations <= 0:
        return 0
    return max(required_registrations * 3, required_registrations + 5, 10)


def run_validate_accounts_command(args: argparse.Namespace) -> int:
    payload, exit_code = _run_validation(args, delete_invalid=False)
    emit_output(payload, args.output, _print_validation_result)
    return exit_code


def run_delete_invalid_accounts_command(args: argparse.Namespace) -> int:
    payload, exit_code = _run_validation(args, delete_invalid=True)
    emit_output(payload, args.output, _print_validation_result)
    return exit_code


def run_ensure_target_accounts_command(args: argparse.Namespace) -> int:
    settings = bootstrap_cli(database_url=args.database_url, log_level=args.log_level)

    validation_snapshots = _load_snapshots(
        explicit_ids=[],
        all_accounts=True,
        status=None,
        search=None,
        limit=None,
    )
    validation_payload, validation_exit_code = _validate_snapshots(
        validation_snapshots,
        proxy=args.proxy,
        refresh_before_validate=args.refresh_before_validate,
        delete_invalid=True,
    )

    available_count = validation_payload["summary"]["valid_count"]
    target_count = args.target_count
    required_registrations = max(target_count - available_count, 0)

    registration_results: list[dict[str, Any]] = []
    attempted_count = 0
    successful_registrations = 0
    max_attempts = args.max_attempts if args.max_attempts is not None else _default_max_attempts(required_registrations)

    service_config = None
    if required_registrations > 0:
        from ..registration import parse_service_config

        service_config = parse_service_config(args.service_config, args.service_config_file)
        register_args = SimpleNamespace(
            database_url=args.database_url,
            log_level=args.log_level,
            output="json",
            service_config=args.service_config,
            service_config_file=args.service_config_file,
            proxy=args.proxy,
            proxy_id=args.proxy_id,
            service_type=args.service_type,
            service_id=args.service_id,
            no_save=False,
            count=1,
            auto_upload_cpa=False,
            cpa_api_url=args.cpa_api_url,
            cpa_api_token=args.cpa_api_token,
            cpa_service_id=args.cpa_service_id,
        )

        while successful_registrations < required_registrations and attempted_count < max_attempts:
            attempted_count += 1
            payload = _run_single_registration(
                register_args,
                settings,
                service_config,
                sequence=attempted_count,
                total_count=max_attempts,
            )
            registration_results.append(payload)
            if payload["success"]:
                successful_registrations += 1

    active_account_ids = _get_active_account_ids()
    final_active_count = len(active_account_ids)

    cpa_sync = None
    cpa_exit_code = 0
    if not args.skip_cpa_sync:
        with get_db() as db:
            target = resolve_cpa_target(
                db,
                settings,
                api_url=args.cpa_api_url,
                api_token=args.cpa_api_token,
                service_id=args.cpa_service_id,
            )
        validate_cpa_target(target)
        batch_result = batch_upload_to_cpa(active_account_ids, api_url=target.api_url, api_token=target.api_token)
        cpa_sync = {
            "success_count": batch_result["success_count"],
            "failed_count": batch_result["failed_count"],
            "skipped_count": batch_result["skipped_count"],
            "details": batch_result["details"],
            "target": {
                "source": target.source,
                "service_id": target.service_id,
                "service_name": target.name,
                "api_url": target.api_url,
            },
            "remote_delete_supported": False,
        }
        cpa_exit_code = 0 if batch_result["failed_count"] == 0 else 1

    payload = {
        "validation": validation_payload,
        "available_count_before_registration": available_count,
        "target_count": target_count,
        "required_registrations": required_registrations,
        "registration": {
            "attempted_count": attempted_count,
            "success_count": sum(1 for item in registration_results if item["success"]),
            "failed_count": sum(1 for item in registration_results if not item["success"]),
            "max_attempts": max_attempts,
            "results": registration_results,
        },
        "final_active_count": final_active_count,
        "cpa_sync": cpa_sync,
    }
    emit_output(payload, args.output, _print_ensure_target_result)

    target_reached = final_active_count >= target_count
    exit_code = 0 if target_reached and validation_exit_code == 0 and cpa_exit_code == 0 else 1
    return exit_code
