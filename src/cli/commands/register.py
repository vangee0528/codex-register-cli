"""Register command implementation."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from typing import Any

from ...core.register import RegistrationEngine
from ...core.upload.cpa_upload import upload_to_cpa
from ...database import crud
from ...database.session import get_db
from ...services import EmailServiceFactory
from ..bootstrap import bootstrap_cli
from ..common import emit_output, positive_int
from ..cpa import build_cpa_token_payload, build_cpa_token_payload_from_account, resolve_cpa_target, validate_cpa_target
from ..registration import parse_service_config, resolve_email_service, resolve_proxy


SERVICE_TYPE_CHOICES = ["tempmail", "outlook", "moe_mail", "temp_mail", "duck_mail", "freemail", "imap_mail"]


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("register", help="register one or more accounts")
    parser.add_argument("--count", type=positive_int, help="temporary override for config.registration.default_count")
    parser.add_argument(
        "--upload-cpa",
        dest="auto_upload_cpa",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="temporarily enable or disable CPA upload after successful registration",
    )
    parser.add_argument("--output", choices=("text", "json"), default="text", help="final result format")

    parser.add_argument("--service-type", choices=SERVICE_TYPE_CHOICES, help=argparse.SUPPRESS)
    parser.add_argument("--service-id", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--service-config", help=argparse.SUPPRESS)
    parser.add_argument("--service-config-file", help=argparse.SUPPRESS)
    parser.add_argument("--proxy", help=argparse.SUPPRESS)
    parser.add_argument("--proxy-id", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--database-url", help=argparse.SUPPRESS)
    parser.add_argument("--log-level", help=argparse.SUPPRESS)
    parser.add_argument("--cpa-api-url", help=argparse.SUPPRESS)
    parser.add_argument("--cpa-api-token", help=argparse.SUPPRESS)
    parser.add_argument("--cpa-service-id", type=int, help=argparse.SUPPRESS)
    parser.add_argument(
        "--save-to-database",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.set_defaults(handler=run_register_command)


def _result_payload(
    result,
    resolved_service,
    proxy_url: str | None,
    proxy_source: str,
    saved_to_database: bool,
    saved_account_id: int | None,
    cpa_upload: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "success": result.success,
        "email": result.email,
        "password": result.password,
        "account_id": result.account_id,
        "workspace_id": result.workspace_id,
        "access_token": result.access_token,
        "refresh_token": result.refresh_token,
        "id_token": result.id_token,
        "session_token": result.session_token,
        "error_message": result.error_message,
        "source": result.source,
        "metadata": result.metadata or {},
        "logs": result.logs or [],
        "saved_to_database": saved_to_database,
        "saved_account_row_id": saved_account_id,
        "email_service": {
            "type": resolved_service.service_type.value,
            "name": resolved_service.name,
            "source": resolved_service.source,
            "id": resolved_service.service_id,
        },
        "proxy": {
            "url": proxy_url,
            "source": proxy_source,
        },
        "cpa_upload": cpa_upload,
    }


def _print_register_text(payload: dict[str, Any]) -> None:
    if payload["success"]:
        print("Registration succeeded")
        print(f"email: {payload['email']}")
        print(f"password: {payload['password']}")
        print(f"account_id: {payload['account_id']}")
        print(f"workspace_id: {payload['workspace_id']}")
        print(f"access_token: {payload['access_token']}")
        print(f"refresh_token: {payload['refresh_token']}")
        print(f"id_token: {payload['id_token']}")
        print(f"session_token: {payload['session_token']}")
        print(f"email_service: {payload['email_service']['type']} ({payload['email_service']['source']})")
        print(f"proxy: {payload['proxy']['url'] or 'none'} ({payload['proxy']['source']})")
        print(f"saved_to_database: {payload['saved_to_database']}")
        if payload["cpa_upload"] is not None:
            print(f"cpa_upload: {payload['cpa_upload']['success']} ({payload['cpa_upload']['message']})")
        return

    print("Registration failed", file=sys.stderr)
    print(f"error: {payload['error_message']}", file=sys.stderr)


def _print_batch_text(payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    print("Batch registration finished")
    print(f"requested: {summary['requested']}")
    print(f"registration_success_count: {summary['registration_success_count']}")
    print(f"registration_failed_count: {summary['registration_failed_count']}")
    if summary["cpa_upload_requested"]:
        print(f"cpa_upload_success_count: {summary['cpa_upload_success_count']}")
        print(f"cpa_upload_failed_count: {summary['cpa_upload_failed_count']}")

    for item in payload["results"]:
        cpa_result = item.get("cpa_upload")
        cpa_text = "not-requested"
        if cpa_result is not None:
            cpa_text = f"{cpa_result['success']}:{cpa_result['message']}"
        print(
            f"#{item['sequence']} success={item['success']} email={item['email'] or '-'} "
            f"saved={item['saved_to_database']} cpa={cpa_text}"
        )


def _upload_registration_to_cpa(args: argparse.Namespace, settings, payload: dict[str, Any]) -> dict[str, Any]:
    with get_db() as db:
        target = resolve_cpa_target(
            db,
            settings,
            api_url=args.cpa_api_url,
            api_token=args.cpa_api_token,
            service_id=args.cpa_service_id,
        )
        proxy_url, _, proxy_source = resolve_proxy(
            db,
            settings,
            behavior="cpa_upload",
            explicit_proxy=args.proxy,
            proxy_id=args.proxy_id,
        )
    validate_cpa_target(target)

    token_payload: dict[str, Any]
    saved_account_id = payload.get("saved_account_row_id")
    if saved_account_id is not None:
        with get_db() as db:
            account = crud.get_account_by_id(db, saved_account_id)
            if account is None:
                raise ValueError(f"saved account {saved_account_id} was not found for CPA upload")
            token_payload = build_cpa_token_payload_from_account(account)
    else:
        token_payload = build_cpa_token_payload(
            email=payload["email"],
            account_id=payload["account_id"],
            access_token=payload["access_token"],
            refresh_token=payload["refresh_token"],
            id_token=payload["id_token"],
            expires_at=None,
            last_refresh=datetime.utcnow(),
        )

    success, message = upload_to_cpa(
        token_payload,
        proxy=proxy_url,
        api_url=target.api_url,
        api_token=target.api_token,
    )

    if success and saved_account_id is not None:
        with get_db() as db:
            crud.update_account(
                db,
                saved_account_id,
                cpa_uploaded=True,
                cpa_uploaded_at=datetime.utcnow(),
            )

    return {
        "success": success,
        "message": message,
        "source": target.source,
        "service_id": target.service_id,
        "service_name": target.name,
        "api_url": target.api_url,
        "proxy": {
            "url": proxy_url,
            "source": proxy_source,
        },
    }


def _run_single_registration(
    args: argparse.Namespace,
    settings,
    service_config: dict[str, Any],
    sequence: int,
    total_count: int,
) -> dict[str, Any]:
    cli_logs_to_stderr = args.output == "json"
    log_stream = sys.stderr if cli_logs_to_stderr else sys.stdout
    prefix = f"[{sequence}/{total_count}] " if total_count > 1 else ""

    def callback_logger(message: str) -> None:
        print(f"{prefix}{message}", file=log_stream)

    with get_db() as db:
        proxy_url, proxy_id, proxy_source = resolve_proxy(
            db,
            settings,
            behavior="registration",
            explicit_proxy=args.proxy,
            proxy_id=args.proxy_id,
        )
        resolved_service = resolve_email_service(
            db,
            settings,
            service_type_name=args.service_type,
            service_id=args.service_id,
            inline_config=service_config,
            proxy_url=proxy_url,
        )

    email_service = EmailServiceFactory.create(
        resolved_service.service_type,
        resolved_service.config,
        name=resolved_service.name,
    )
    engine = RegistrationEngine(
        email_service=email_service,
        proxy_url=proxy_url,
        callback_logger=callback_logger,
    )
    result = engine.run()

    saved_to_database = False
    saved_account_id: int | None = None
    if result.success and args.save_to_database:
        saved_to_database = engine.save_to_database(result)
        if saved_to_database:
            with get_db() as db:
                account = crud.get_account_by_email(db, result.email)
                if account is not None:
                    saved_account_id = account.id
                if proxy_id is not None:
                    crud.update_proxy_last_used(db, proxy_id)

    payload = _result_payload(
        result=result,
        resolved_service=resolved_service,
        proxy_url=proxy_url,
        proxy_source=proxy_source,
        saved_to_database=saved_to_database,
        saved_account_id=saved_account_id,
        cpa_upload=None,
    )

    if result.success and args.auto_upload_cpa:
        payload["cpa_upload"] = _upload_registration_to_cpa(args, settings, payload)

    payload["sequence"] = sequence
    return payload


def run_register_command(args: argparse.Namespace) -> int:
    settings = bootstrap_cli(database_url=args.database_url, log_level=args.log_level)

    args.count = args.count or settings.registration.default_count
    if args.auto_upload_cpa is None:
        args.auto_upload_cpa = settings.registration.auto_upload_cpa
    if args.save_to_database is None:
        args.save_to_database = settings.registration.save_to_database

    service_config = {
        **settings.registration.service_config,
        **parse_service_config(args.service_config, args.service_config_file),
    }

    results = [
        _run_single_registration(args, settings, service_config, sequence=index, total_count=args.count)
        for index in range(1, args.count + 1)
    ]

    if args.count == 1:
        payload = results[0]
        emit_output(payload, args.output, _print_register_text)
        registration_ok = payload["success"]
        cpa_ok = payload["cpa_upload"] is None or payload["cpa_upload"]["success"]
        return 0 if registration_ok and cpa_ok else 1

    cpa_upload_success_count = sum(1 for item in results if item.get("cpa_upload") is not None and item["cpa_upload"]["success"])
    cpa_upload_failed_count = sum(1 for item in results if item.get("cpa_upload") is not None and not item["cpa_upload"]["success"])
    summary = {
        "requested": args.count,
        "registration_success_count": sum(1 for item in results if item["success"]),
        "registration_failed_count": sum(1 for item in results if not item["success"]),
        "cpa_upload_requested": args.auto_upload_cpa,
        "cpa_upload_success_count": cpa_upload_success_count,
        "cpa_upload_failed_count": cpa_upload_failed_count,
    }
    payload = {
        "summary": summary,
        "results": results,
    }
    emit_output(payload, args.output, _print_batch_text)

    registrations_ok = summary["registration_failed_count"] == 0
    cpa_ok = (not args.auto_upload_cpa) or summary["cpa_upload_failed_count"] == 0
    return 0 if registrations_ok and cpa_ok else 1
