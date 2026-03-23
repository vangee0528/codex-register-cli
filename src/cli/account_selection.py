"""Account selection helpers shared by CLI commands."""

from __future__ import annotations

import argparse
from typing import Iterable

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database.models import Account
from .common import dedupe_preserve_order, parse_csv_ints


ACCOUNT_STATUS_CHOICES = ("active", "expired", "banned", "failed")


def add_account_selection_arguments(parser: argparse.ArgumentParser, *, include_proxy: bool = False) -> None:
    parser.add_argument(
        "--account-id",
        dest="account_ids",
        action="append",
        type=int,
        default=[],
        help="select a specific account id; repeat the flag to select multiple accounts",
    )
    parser.add_argument(
        "--account-ids",
        dest="account_ids_csv",
        help="comma-separated list of account ids",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="select all accounts matching the optional filters",
    )
    parser.add_argument(
        "--status",
        choices=ACCOUNT_STATUS_CHOICES,
        help="status filter used with --all",
    )
    parser.add_argument("--search", help="substring match on email, account id, or workspace id when using --all")
    parser.add_argument("--limit", type=int, help="optional row limit when using --all")
    if include_proxy:
        parser.add_argument("--proxy", help="proxy URL used for token validation/refresh requests")


def resolve_explicit_account_ids(account_ids: Iterable[int], csv_ids: str | None) -> list[int]:
    combined = list(account_ids) + parse_csv_ints(csv_ids)
    return dedupe_preserve_order(combined)


def select_accounts(
    db: Session,
    *,
    explicit_ids: list[int],
    all_accounts: bool,
    status: str | None = None,
    search: str | None = None,
    limit: int | None = None,
    only_not_uploaded: bool = False,
) -> list[Account]:
    if explicit_ids:
        records = db.query(Account).filter(Account.id.in_(explicit_ids)).order_by(Account.id.asc()).all()
        record_map = {record.id: record for record in records}
        return [record_map[account_id] for account_id in explicit_ids if account_id in record_map]

    if not all_accounts:
        raise ValueError("select accounts with --account-id/--account-ids or use --all")

    query = db.query(Account)

    if status:
        query = query.filter(Account.status == status)

    if search:
        like_value = f"%{search}%"
        query = query.filter(
            or_(
                Account.email.ilike(like_value),
                Account.account_id.ilike(like_value),
                Account.workspace_id.ilike(like_value),
            )
        )

    if only_not_uploaded:
        query = query.filter(or_(Account.cpa_uploaded == False, Account.cpa_uploaded.is_(None)))

    query = query.order_by(Account.id.asc())
    if limit is not None:
        query = query.limit(limit)

    return query.all()
