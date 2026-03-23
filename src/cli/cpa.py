"""CPA-related CLI helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from ..database import crud
from ..database.models import Account


@dataclass
class ResolvedCpaTarget:
    api_url: str
    api_token: str
    source: str
    name: str
    service_id: int | None = None


def _format_cpa_datetime(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%S+08:00") if value else ""


def build_cpa_token_payload(
    *,
    email: str,
    account_id: str | None,
    access_token: str | None,
    refresh_token: str | None,
    id_token: str | None,
    expires_at: datetime | None,
    last_refresh: datetime | None,
) -> dict[str, Any]:
    return {
        "type": "codex",
        "email": email,
        "expired": _format_cpa_datetime(expires_at),
        "id_token": id_token or "",
        "account_id": account_id or "",
        "access_token": access_token or "",
        "last_refresh": _format_cpa_datetime(last_refresh),
        "refresh_token": refresh_token or "",
    }


def build_cpa_token_payload_from_account(account: Account) -> dict[str, Any]:
    return build_cpa_token_payload(
        email=account.email,
        account_id=account.account_id,
        access_token=account.access_token,
        refresh_token=account.refresh_token,
        id_token=account.id_token,
        expires_at=account.expires_at,
        last_refresh=account.last_refresh,
    )


def resolve_cpa_target(
    db: Session,
    settings,
    *,
    api_url: str | None = None,
    api_token: str | None = None,
    service_id: int | None = None,
) -> ResolvedCpaTarget:
    if api_url or api_token:
        effective_token = api_token or settings.cpa_api_token.get_secret_value()
        return ResolvedCpaTarget(
            api_url=api_url or settings.cpa_api_url,
            api_token=effective_token,
            source="arguments",
            name="arguments",
            service_id=None,
        )

    if service_id is not None:
        for service in settings.cpa_services:
            if service.id == service_id:
                if not service.enabled:
                    raise ValueError(f"cpa service id {service_id} is disabled")
                return ResolvedCpaTarget(
                    api_url=service.api_url,
                    api_token=service.api_token,
                    source="config-file-id",
                    name=service.name,
                    service_id=service.id,
                )

        service = crud.get_cpa_service_by_id(db, service_id)
        if not service:
            raise ValueError(f"cpa service id {service_id} was not found")
        if not service.enabled:
            raise ValueError(f"cpa service id {service_id} is disabled")
        return ResolvedCpaTarget(
            api_url=service.api_url,
            api_token=service.api_token,
            source="database-id",
            name=service.name,
            service_id=service.id,
        )

    enabled_config_services = [service for service in settings.cpa_services if service.enabled]
    if enabled_config_services:
        enabled_config_services.sort(key=lambda item: (item.priority, item.id))
        service = enabled_config_services[0]
        return ResolvedCpaTarget(
            api_url=service.api_url,
            api_token=service.api_token,
            source="config-file-default",
            name=service.name,
            service_id=service.id,
        )

    services = crud.get_cpa_services(db, enabled=True)
    if services:
        service = services[0]
        return ResolvedCpaTarget(
            api_url=service.api_url,
            api_token=service.api_token,
            source="database-default",
            name=service.name,
            service_id=service.id,
        )

    return ResolvedCpaTarget(
        api_url=settings.cpa_api_url,
        api_token=settings.cpa_api_token.get_secret_value(),
        source="config-file",
        name="config-file",
        service_id=None,
    )


def validate_cpa_target(target: ResolvedCpaTarget) -> None:
    if not target.api_url:
        raise ValueError("CPA API URL is not configured")
    if not target.api_token:
        raise ValueError("CPA API token is not configured")
