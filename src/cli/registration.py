"""CLI-specific registration orchestration helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ..config.constants import EmailServiceType
from ..config.settings import Settings
from ..database import crud
from ..database.models import EmailService, Proxy


@dataclass
class ResolvedEmailService:
    service_type: EmailServiceType
    config: dict[str, Any]
    source: str
    name: str
    service_id: int | None = None


def parse_service_config(inline_json: str | None, config_file: str | None) -> dict[str, Any]:
    config: dict[str, Any] = {}

    if config_file:
        with Path(config_file).open(encoding="utf-8") as handle:
            file_config = json.load(handle)
        if not isinstance(file_config, dict):
            raise ValueError("service config file must contain a JSON object")
        config.update(file_config)

    if inline_json:
        inline_config = json.loads(inline_json)
        if not isinstance(inline_config, dict):
            raise ValueError("inline service config must be a JSON object")
        config.update(inline_config)

    return config


def normalize_email_service_config(
    service_type: EmailServiceType,
    config: dict[str, Any] | None,
    proxy_url: str | None = None,
) -> dict[str, Any]:
    normalized = dict(config or {})

    if "api_url" in normalized and "base_url" not in normalized:
        normalized["base_url"] = normalized.pop("api_url")

    if service_type == EmailServiceType.MOE_MAIL:
        if "domain" in normalized and "default_domain" not in normalized:
            normalized["default_domain"] = normalized.pop("domain")
    elif service_type in (EmailServiceType.TEMP_MAIL, EmailServiceType.FREEMAIL):
        if "default_domain" in normalized and "domain" not in normalized:
            normalized["domain"] = normalized.pop("default_domain")
    elif service_type == EmailServiceType.DUCK_MAIL:
        if "domain" in normalized and "default_domain" not in normalized:
            normalized["default_domain"] = normalized.pop("domain")

    if proxy_url and "proxy_url" not in normalized:
        normalized["proxy_url"] = proxy_url

    return normalized


def build_default_service_config(
    service_type: EmailServiceType,
    settings: Settings,
    proxy_url: str | None,
) -> dict[str, Any]:
    if service_type == EmailServiceType.TEMPMAIL:
        return {
            "base_url": settings.tempmail_base_url,
            "timeout": settings.tempmail_timeout,
            "max_retries": settings.tempmail_max_retries,
            "proxy_url": proxy_url,
        }

    if service_type == EmailServiceType.MOE_MAIL:
        return normalize_email_service_config(
            service_type,
            {
                "base_url": settings.custom_domain_base_url,
                "api_key": settings.custom_domain_api_key.get_secret_value(),
            },
            proxy_url=proxy_url,
        )

    return normalize_email_service_config(service_type, {}, proxy_url=proxy_url)


def _get_config_proxy_by_id(settings: Settings, proxy_id: int):
    for proxy in settings.proxies:
        if proxy.id == proxy_id:
            return proxy
    return None


def resolve_proxy(
    db: Session,
    settings: Settings,
    explicit_proxy: str | None = None,
    proxy_id: int | None = None,
) -> tuple[str | None, int | None, str]:
    if explicit_proxy:
        return explicit_proxy, None, "argument"

    if proxy_id is not None:
        config_proxy = _get_config_proxy_by_id(settings, proxy_id)
        if config_proxy:
            if not config_proxy.enabled:
                raise ValueError(f"proxy id {proxy_id} is disabled")
            return config_proxy.resolved_url, config_proxy.id, "config-file-id"

        db_proxy = crud.get_proxy_by_id(db, proxy_id)
        if not db_proxy:
            raise ValueError(f"proxy id {proxy_id} was not found")
        if not db_proxy.enabled:
            raise ValueError(f"proxy id {proxy_id} is disabled")
        return db_proxy.proxy_url, db_proxy.id, "database-id"

    if settings.proxy_url:
        return settings.proxy_url, None, "config-file"

    enabled_config_proxies = [proxy for proxy in settings.proxies if proxy.enabled and proxy.resolved_url]
    if enabled_config_proxies:
        enabled_config_proxies.sort(key=lambda item: (not item.is_default, item.id))
        selected = enabled_config_proxies[0]
        return selected.resolved_url, selected.id, "config-file-default"

    db_proxy = crud.get_random_proxy(db)
    if db_proxy:
        return db_proxy.proxy_url, db_proxy.id, "database-default"

    return None, None, "none"


def _get_config_service_by_id(settings: Settings, service_id: int):
    for service in settings.email_services:
        if service.id == service_id:
            return service
    return None


def _get_enabled_service_by_type(db: Session, settings: Settings, service_type: EmailServiceType):
    config_services = [
        service
        for service in settings.email_services
        if service.type == service_type.value and service.enabled
    ]
    if config_services:
        config_services.sort(key=lambda item: (item.priority, item.id))
        return config_services[0], "config-file"

    db_service = (
        db.query(EmailService)
        .filter(EmailService.service_type == service_type.value, EmailService.enabled == True)
        .order_by(EmailService.priority.asc(), EmailService.id.asc())
        .first()
    )
    if db_service:
        return db_service, "database"

    return None, "none"


def resolve_email_service(
    db: Session,
    settings: Settings,
    service_type_name: str | None,
    service_id: int | None,
    inline_config: dict[str, Any],
    proxy_url: str | None,
) -> ResolvedEmailService:
    requested_type = EmailServiceType(service_type_name or EmailServiceType.TEMPMAIL.value)

    if service_id is not None:
        config_service = _get_config_service_by_id(settings, service_id)
        if config_service:
            if not config_service.enabled:
                raise ValueError(f"email service id {service_id} is disabled")
            config_service_type = EmailServiceType(config_service.type)
            merged = {**config_service.config, **inline_config}
            return ResolvedEmailService(
                service_type=config_service_type,
                config=normalize_email_service_config(config_service_type, merged, proxy_url=proxy_url),
                source="config-file-id",
                name=config_service.name,
                service_id=config_service.id,
            )

        db_service = crud.get_email_service_by_id(db, service_id)
        if not db_service:
            raise ValueError(f"email service id {service_id} was not found")
        if not db_service.enabled:
            raise ValueError(f"email service id {service_id} is disabled")

        db_service_type = EmailServiceType(db_service.service_type)
        merged = {**(db_service.config or {}), **inline_config}
        return ResolvedEmailService(
            service_type=db_service_type,
            config=normalize_email_service_config(db_service_type, merged, proxy_url=proxy_url),
            source="database-id",
            name=db_service.name,
            service_id=db_service.id,
        )

    configured_service, source = _get_enabled_service_by_type(db, settings, requested_type)
    if configured_service is not None:
        if source == "config-file":
            merged = {**configured_service.config, **inline_config}
            return ResolvedEmailService(
                service_type=requested_type,
                config=normalize_email_service_config(requested_type, merged, proxy_url=proxy_url),
                source="config-file-default",
                name=configured_service.name,
                service_id=configured_service.id,
            )

        merged = {**(configured_service.config or {}), **inline_config}
        return ResolvedEmailService(
            service_type=requested_type,
            config=normalize_email_service_config(requested_type, merged, proxy_url=proxy_url),
            source="database-default",
            name=configured_service.name,
            service_id=configured_service.id,
        )

    default_config = build_default_service_config(requested_type, settings, proxy_url)
    merged = {**default_config, **inline_config}
    return ResolvedEmailService(
        service_type=requested_type,
        config=normalize_email_service_config(requested_type, merged, proxy_url=proxy_url),
        source="settings-default",
        name=requested_type.value,
        service_id=None,
    )


def list_available_services(db: Session, settings: Settings) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = [
        {
            "id": None,
            "name": "Tempmail.lol",
            "type": EmailServiceType.TEMPMAIL.value,
            "enabled": True,
            "source": "settings-default",
            "summary": {
                "base_url": settings.tempmail_base_url,
            },
        }
    ]

    for service in sorted(settings.email_services, key=lambda item: (item.priority, item.id)):
        summary = {}
        for key in ("email", "domain", "default_domain", "base_url", "host"):
            value = service.config.get(key)
            if value:
                summary[key] = value
        records.append(
            {
                "id": service.id,
                "name": service.name,
                "type": service.type,
                "enabled": bool(service.enabled),
                "source": "config-file",
                "summary": summary,
            }
        )

    for service in db.query(EmailService).order_by(EmailService.priority.asc(), EmailService.id.asc()).all():
        summary = {}
        for key in ("email", "domain", "default_domain", "base_url", "host"):
            value = (service.config or {}).get(key)
            if value:
                summary[key] = value

        records.append(
            {
                "id": service.id,
                "name": service.name,
                "type": service.service_type,
                "enabled": bool(service.enabled),
                "source": "database-legacy",
                "summary": summary,
            }
        )

    return records


def list_available_proxies(db: Session, settings: Settings) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    if settings.proxy_url:
        records.append(
            {
                "id": None,
                "name": "settings.proxy_url",
                "enabled": True,
                "source": "config-file",
                "proxy_url": settings.proxy_url,
            }
        )

    for proxy in sorted(settings.proxies, key=lambda item: (not item.is_default, item.id)):
        records.append(
            {
                "id": proxy.id,
                "name": proxy.name,
                "enabled": bool(proxy.enabled),
                "source": "config-file",
                "proxy_url": proxy.resolved_url,
                "is_default": bool(proxy.is_default),
            }
        )

    for proxy in db.query(Proxy).order_by(Proxy.is_default.desc(), Proxy.id.asc()).all():
        records.append(
            {
                "id": proxy.id,
                "name": proxy.name,
                "enabled": bool(proxy.enabled),
                "source": "database-legacy",
                "proxy_url": proxy.proxy_url,
                "is_default": bool(proxy.is_default),
            }
        )

    return records
