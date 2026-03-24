"""File-backed application settings for the CLI-first build."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, SecretStr, field_validator


class EmailServiceResource(BaseModel):
    id: int
    name: str
    type: str
    enabled: bool = True
    priority: int = 0
    config: Dict[str, Any] = Field(default_factory=dict)


class ProxyResource(BaseModel):
    id: int
    name: str
    enabled: bool = True
    is_default: bool = False
    proxy_url: str = ""
    type: str = "http"
    host: str = ""
    port: int = 0
    username: str = ""
    password: str = ""

    @property
    def resolved_url(self) -> str:
        if self.proxy_url:
            return self.proxy_url
        if not self.host or not self.port:
            return ""
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        return f"{self.type}://{auth}{self.host}:{self.port}"


class CpaServiceResource(BaseModel):
    id: int
    name: str
    api_url: str
    api_token: str
    enabled: bool = True
    priority: int = 0


class AppSettings(BaseModel):
    name: str = "Codex CLI registration system"
    version: str = "2.2.0"
    debug: bool = False


class RuntimeSettings(BaseModel):
    database_url: str = "data/database.db"
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    log_retention_days: int = 30

    @field_validator("database_url", mode="before")
    @classmethod
    def validate_database_url(cls, value: Any) -> str:
        return Settings.validate_database_url(value)


class OpenAISettings(BaseModel):
    client_id: str = "app_EMoamEEZ73f0CkXaXp7hrann"
    auth_url: str = "https://auth.openai.com/oauth/authorize"
    token_url: str = "https://auth.openai.com/oauth/token"
    redirect_uri: str = "http://localhost:1455/auth/callback"
    scope: str = "openid email profile offline_access"


class UiSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8765


class DefaultSelections(BaseModel):
    email_service_type: str = "tempmail"
    email_service_id: int | None = None
    proxy_id: int | None = None
    cpa_service_id: int | None = None


class ResourceSettings(BaseModel):
    defaults: DefaultSelections = Field(default_factory=DefaultSelections)
    proxies: List[ProxyResource] = Field(default_factory=list)
    email_services: List[EmailServiceResource] = Field(default_factory=list)
    cpa_services: List[CpaServiceResource] = Field(default_factory=list)


class RegistrationDefaults(BaseModel):
    default_count: int = Field(default=1, ge=1)
    auto_upload_cpa: bool = False
    save_to_database: bool = True
    service_config: Dict[str, Any] = Field(default_factory=dict)


class WorkflowDefaults(BaseModel):
    target_account_count: int = Field(default=10, ge=1)
    refresh_before_validate: bool = True
    auto_delete_invalid: bool = True
    auto_sync_cpa: bool = False
    max_registration_attempts: int = Field(default=0, ge=0)


class ProxyPolicy(BaseModel):
    registration: bool = True
    account_validate: bool = True
    token_refresh: bool = True
    cpa_upload: bool = False
    cpa_test: bool = False


class DynamicProxySettings(BaseModel):
    enabled: bool = False
    api_url: str = ""
    api_key: SecretStr = SecretStr("")
    api_key_header: str = "X-API-Key"
    result_field: str = ""


class StaticProxySettings(BaseModel):
    enabled: bool = False
    type: str = "http"
    host: str = "127.0.0.1"
    port: int = 7890
    username: str = ""
    password: SecretStr = SecretStr("")

    @property
    def resolved_url(self) -> Optional[str]:
        if not self.enabled or not self.host or not self.port:
            return None
        auth = ""
        password = self.password.get_secret_value()
        if self.username and password:
            auth = f"{self.username}:{password}@"
        return f"{self.type}://{auth}{self.host}:{self.port}"


class ProxySettings(BaseModel):
    static: StaticProxySettings = Field(default_factory=StaticProxySettings)
    policy: ProxyPolicy = Field(default_factory=ProxyPolicy)
    dynamic: DynamicProxySettings = Field(default_factory=DynamicProxySettings)


class TempmailSettings(BaseModel):
    base_url: str = "https://api.tempmail.lol/v2"
    timeout: int = 30
    max_retries: int = 3


class CustomDomainMailSettings(BaseModel):
    base_url: str = ""
    api_key: SecretStr = SecretStr("")


class VerificationMailSettings(BaseModel):
    code_timeout: int = 120
    code_poll_interval: int = 3


class OutlookMailSettings(BaseModel):
    provider_priority: List[str] = Field(default_factory=lambda: ["imap_old", "imap_new", "graph_api"])
    health_failure_threshold: int = 5
    health_disable_duration: int = 60
    default_client_id: str = "24d9a0ed-8787-4584-883c-2fd79308940a"


class MailSettings(BaseModel):
    tempmail: TempmailSettings = Field(default_factory=TempmailSettings)
    custom_domain: CustomDomainMailSettings = Field(default_factory=CustomDomainMailSettings)
    verification: VerificationMailSettings = Field(default_factory=VerificationMailSettings)
    outlook: OutlookMailSettings = Field(default_factory=OutlookMailSettings)


class CpaLocalFilesSettings(BaseModel):
    enabled: bool = False
    path: str = "~/.cli-proxy-api"
    trash_dir: str = ""


class CpaSettings(BaseModel):
    enabled: bool = False
    api_url: str = ""
    api_token: SecretStr = SecretStr("")
    local_files: CpaLocalFilesSettings = Field(default_factory=CpaLocalFilesSettings)


class Settings(BaseModel):
    app: AppSettings = Field(default_factory=AppSettings)
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    ui: UiSettings = Field(default_factory=UiSettings)
    resources: ResourceSettings = Field(default_factory=ResourceSettings)
    registration: RegistrationDefaults = Field(default_factory=RegistrationDefaults)
    workflow: WorkflowDefaults = Field(default_factory=WorkflowDefaults)
    proxy: ProxySettings = Field(default_factory=ProxySettings)
    mail: MailSettings = Field(default_factory=MailSettings)
    cpa: CpaSettings = Field(default_factory=CpaSettings)

    @field_validator("runtime", mode="before")
    @classmethod
    def _validate_runtime(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        if "database_url" in normalized:
            normalized["database_url"] = cls.validate_database_url(normalized["database_url"])
        return normalized

    @classmethod
    def validate_database_url(cls, value: Any) -> str:
        if not isinstance(value, str):
            return value
        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value[len("postgres://"):]
        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value[len("postgresql://"):]
        if value.startswith(("postgresql+psycopg://", "sqlite:///", "mysql://")):
            return value
        if os.path.isabs(value) or ":/" not in value:
            return f"sqlite:///{value}"
        return value

    @property
    def app_name(self) -> str:
        return self.app.name

    @property
    def app_version(self) -> str:
        return self.app.version

    @property
    def debug(self) -> bool:
        return self.app.debug

    @property
    def database_url(self) -> str:
        return self.runtime.database_url

    @property
    def log_level(self) -> str:
        return self.runtime.log_level

    @property
    def log_file(self) -> str:
        return self.runtime.log_file

    @property
    def log_retention_days(self) -> int:
        return self.runtime.log_retention_days

    @property
    def openai_client_id(self) -> str:
        return self.openai.client_id

    @property
    def openai_auth_url(self) -> str:
        return self.openai.auth_url

    @property
    def openai_token_url(self) -> str:
        return self.openai.token_url

    @property
    def openai_redirect_uri(self) -> str:
        return self.openai.redirect_uri

    @property
    def openai_scope(self) -> str:
        return self.openai.scope

    @property
    def proxy_enabled(self) -> bool:
        return self.proxy.static.enabled

    @property
    def proxy_type(self) -> str:
        return self.proxy.static.type

    @property
    def proxy_host(self) -> str:
        return self.proxy.static.host

    @property
    def proxy_port(self) -> int:
        return self.proxy.static.port

    @property
    def proxy_username(self) -> str:
        return self.proxy.static.username

    @property
    def proxy_password(self) -> SecretStr:
        return self.proxy.static.password

    @property
    def proxy_policy(self) -> ProxyPolicy:
        return self.proxy.policy

    @property
    def proxy_dynamic(self) -> DynamicProxySettings:
        return self.proxy.dynamic

    @property
    def proxy_url(self) -> Optional[str]:
        return self.proxy.static.resolved_url

    @property
    def tempmail_base_url(self) -> str:
        return self.mail.tempmail.base_url

    @property
    def tempmail_timeout(self) -> int:
        return self.mail.tempmail.timeout

    @property
    def tempmail_max_retries(self) -> int:
        return self.mail.tempmail.max_retries

    @property
    def custom_domain_base_url(self) -> str:
        return self.mail.custom_domain.base_url

    @property
    def custom_domain_api_key(self) -> SecretStr:
        return self.mail.custom_domain.api_key

    @property
    def email_code_timeout(self) -> int:
        return self.mail.verification.code_timeout

    @property
    def email_code_poll_interval(self) -> int:
        return self.mail.verification.code_poll_interval

    @property
    def outlook_provider_priority(self) -> List[str]:
        return self.mail.outlook.provider_priority

    @property
    def outlook_health_failure_threshold(self) -> int:
        return self.mail.outlook.health_failure_threshold

    @property
    def outlook_health_disable_duration(self) -> int:
        return self.mail.outlook.health_disable_duration

    @property
    def outlook_default_client_id(self) -> str:
        return self.mail.outlook.default_client_id

    @property
    def config_ui_host(self) -> str:
        return self.ui.host

    @property
    def config_ui_port(self) -> int:
        return self.ui.port

    @property
    def defaults(self) -> DefaultSelections:
        return self.resources.defaults

    @property
    def proxies(self) -> List[ProxyResource]:
        return self.resources.proxies

    @property
    def email_services(self) -> List[EmailServiceResource]:
        return self.resources.email_services

    @property
    def cpa_services(self) -> List[CpaServiceResource]:
        return self.resources.cpa_services

    @property
    def cpa_enabled(self) -> bool:
        return self.cpa.enabled

    @property
    def cpa_api_url(self) -> str:
        return self.cpa.api_url

    @property
    def cpa_api_token(self) -> SecretStr:
        return self.cpa.api_token


_settings: Optional[Settings] = None
_MISSING = object()


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_config_path() -> Path:
    configured = os.environ.get("APP_CONFIG_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return get_project_root() / "config.json"


def _first_defined(*values: Any, default: Any = None) -> Any:
    for value in values:
        if value is not _MISSING and value is not None:
            return value
    return default


def _deep_merge(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        merged: dict[str, Any] = {key: deepcopy(value) for key, value in base.items()}
        for key, value in override.items():
            if key in merged:
                merged[key] = _deep_merge(merged[key], value)
            else:
                merged[key] = deepcopy(value)
        return merged
    return deepcopy(override)


def _default_settings() -> Settings:
    env_url = os.environ.get("APP_DATABASE_URL") or os.environ.get("DATABASE_URL")
    settings = Settings()
    if env_url:
        settings.runtime.database_url = Settings.validate_database_url(env_url)
    return settings


def _settings_to_json_dict(settings: Settings) -> dict[str, Any]:
    return {
        "app": {
            "name": settings.app.name,
            "version": settings.app.version,
            "debug": settings.app.debug,
        },
        "runtime": {
            "database_url": settings.runtime.database_url,
            "log_level": settings.runtime.log_level,
            "log_file": settings.runtime.log_file,
            "log_retention_days": settings.runtime.log_retention_days,
        },
        "openai": {
            "client_id": settings.openai.client_id,
            "auth_url": settings.openai.auth_url,
            "token_url": settings.openai.token_url,
            "redirect_uri": settings.openai.redirect_uri,
            "scope": settings.openai.scope,
        },
        "ui": {
            "host": settings.ui.host,
            "port": settings.ui.port,
        },
        "resources": {
            "defaults": settings.resources.defaults.model_dump(),
            "proxies": [proxy.model_dump() for proxy in settings.resources.proxies],
            "email_services": [service.model_dump() for service in settings.resources.email_services],
            "cpa_services": [service.model_dump() for service in settings.resources.cpa_services],
        },
        "registration": {
            "default_count": settings.registration.default_count,
            "auto_upload_cpa": settings.registration.auto_upload_cpa,
            "save_to_database": settings.registration.save_to_database,
            "service_config": settings.registration.service_config,
        },
        "workflow": {
            "target_account_count": settings.workflow.target_account_count,
            "refresh_before_validate": settings.workflow.refresh_before_validate,
            "auto_delete_invalid": settings.workflow.auto_delete_invalid,
            "auto_sync_cpa": settings.workflow.auto_sync_cpa,
            "max_registration_attempts": settings.workflow.max_registration_attempts,
        },
        "proxy": {
            "static": {
                "enabled": settings.proxy.static.enabled,
                "type": settings.proxy.static.type,
                "host": settings.proxy.static.host,
                "port": settings.proxy.static.port,
                "username": settings.proxy.static.username,
                "password": settings.proxy.static.password.get_secret_value(),
            },
            "policy": settings.proxy.policy.model_dump(),
            "dynamic": {
                "enabled": settings.proxy.dynamic.enabled,
                "api_url": settings.proxy.dynamic.api_url,
                "api_key": settings.proxy.dynamic.api_key.get_secret_value(),
                "api_key_header": settings.proxy.dynamic.api_key_header,
                "result_field": settings.proxy.dynamic.result_field,
            },
        },
        "mail": {
            "tempmail": settings.mail.tempmail.model_dump(),
            "custom_domain": {
                "base_url": settings.mail.custom_domain.base_url,
                "api_key": settings.mail.custom_domain.api_key.get_secret_value(),
            },
            "verification": settings.mail.verification.model_dump(),
            "outlook": settings.mail.outlook.model_dump(),
        },
        "cpa": {
            "enabled": settings.cpa.enabled,
            "api_url": settings.cpa.api_url,
            "api_token": settings.cpa.api_token.get_secret_value(),
            "local_files": settings.cpa.local_files.model_dump(),
        },
    }


def _normalize_config_shape(raw: dict[str, Any]) -> dict[str, Any]:
    app_section = raw.get("app") or {}
    runtime_section = raw.get("runtime") or {}
    openai_section = raw.get("openai") or {}
    ui_section = raw.get("ui") or {}
    resources_section = raw.get("resources") or {}
    defaults_section = resources_section.get("defaults") or raw.get("defaults") or {}
    registration_section = raw.get("registration") or {}
    workflow_section = raw.get("workflow") or {}
    proxy_section = raw.get("proxy") or {}
    proxy_static_section = proxy_section.get("static") or {}
    proxy_policy_section = proxy_section.get("policy") or raw.get("proxy_policy") or {}
    proxy_dynamic_section = proxy_section.get("dynamic") or raw.get("proxy_dynamic") or {}
    mail_section = raw.get("mail") or {}
    tempmail_section = mail_section.get("tempmail") or {}
    custom_domain_section = mail_section.get("custom_domain") or {}
    verification_section = mail_section.get("verification") or {}
    outlook_section = mail_section.get("outlook") or {}
    cpa_section = raw.get("cpa") or {}
    cpa_local_files_section = cpa_section.get("local_files") or raw.get("cpa_local_files") or raw.get("cpa_local_auth") or {}

    return {
        "app": {
            "name": _first_defined(app_section.get("name", _MISSING), raw.get("app_name", _MISSING), default=AppSettings().name),
            "version": _first_defined(app_section.get("version", _MISSING), raw.get("app_version", _MISSING), default=AppSettings().version),
            "debug": _first_defined(app_section.get("debug", _MISSING), raw.get("debug", _MISSING), default=AppSettings().debug),
        },
        "runtime": {
            "database_url": _first_defined(runtime_section.get("database_url", _MISSING), raw.get("database_url", _MISSING), default=RuntimeSettings().database_url),
            "log_level": _first_defined(runtime_section.get("log_level", _MISSING), raw.get("log_level", _MISSING), default=RuntimeSettings().log_level),
            "log_file": _first_defined(runtime_section.get("log_file", _MISSING), raw.get("log_file", _MISSING), default=RuntimeSettings().log_file),
            "log_retention_days": _first_defined(runtime_section.get("log_retention_days", _MISSING), raw.get("log_retention_days", _MISSING), default=RuntimeSettings().log_retention_days),
        },
        "openai": {
            "client_id": _first_defined(openai_section.get("client_id", _MISSING), raw.get("openai_client_id", _MISSING), default=OpenAISettings().client_id),
            "auth_url": _first_defined(openai_section.get("auth_url", _MISSING), raw.get("openai_auth_url", _MISSING), default=OpenAISettings().auth_url),
            "token_url": _first_defined(openai_section.get("token_url", _MISSING), raw.get("openai_token_url", _MISSING), default=OpenAISettings().token_url),
            "redirect_uri": _first_defined(openai_section.get("redirect_uri", _MISSING), raw.get("openai_redirect_uri", _MISSING), default=OpenAISettings().redirect_uri),
            "scope": _first_defined(openai_section.get("scope", _MISSING), raw.get("openai_scope", _MISSING), default=OpenAISettings().scope),
        },
        "ui": {
            "host": _first_defined(ui_section.get("host", _MISSING), raw.get("config_ui_host", _MISSING), default=UiSettings().host),
            "port": _first_defined(ui_section.get("port", _MISSING), raw.get("config_ui_port", _MISSING), default=UiSettings().port),
        },
        "resources": {
            "defaults": {
                "email_service_type": _first_defined(defaults_section.get("email_service_type", _MISSING), default=DefaultSelections().email_service_type),
                "email_service_id": _first_defined(defaults_section.get("email_service_id", _MISSING)),
                "proxy_id": _first_defined(defaults_section.get("proxy_id", _MISSING)),
                "cpa_service_id": _first_defined(defaults_section.get("cpa_service_id", _MISSING)),
            },
            "proxies": _first_defined(resources_section.get("proxies", _MISSING), raw.get("proxies", _MISSING), default=[]),
            "email_services": _first_defined(resources_section.get("email_services", _MISSING), raw.get("email_services", _MISSING), default=[]),
            "cpa_services": _first_defined(resources_section.get("cpa_services", _MISSING), raw.get("cpa_services", _MISSING), default=[]),
        },
        "registration": {
            "default_count": _first_defined(registration_section.get("default_count", _MISSING), default=RegistrationDefaults().default_count),
            "auto_upload_cpa": _first_defined(registration_section.get("auto_upload_cpa", _MISSING), default=RegistrationDefaults().auto_upload_cpa),
            "save_to_database": _first_defined(registration_section.get("save_to_database", _MISSING), default=RegistrationDefaults().save_to_database),
            "service_config": _first_defined(registration_section.get("service_config", _MISSING), default={}),
        },
        "workflow": {
            "target_account_count": _first_defined(workflow_section.get("target_account_count", _MISSING), default=WorkflowDefaults().target_account_count),
            "refresh_before_validate": _first_defined(workflow_section.get("refresh_before_validate", _MISSING), default=WorkflowDefaults().refresh_before_validate),
            "auto_delete_invalid": _first_defined(workflow_section.get("auto_delete_invalid", _MISSING), default=WorkflowDefaults().auto_delete_invalid),
            "auto_sync_cpa": _first_defined(workflow_section.get("auto_sync_cpa", _MISSING), default=WorkflowDefaults().auto_sync_cpa),
            "max_registration_attempts": _first_defined(workflow_section.get("max_registration_attempts", _MISSING), default=WorkflowDefaults().max_registration_attempts),
        },
        "proxy": {
            "static": {
                "enabled": _first_defined(proxy_static_section.get("enabled", _MISSING), raw.get("proxy_enabled", _MISSING), default=StaticProxySettings().enabled),
                "type": _first_defined(proxy_static_section.get("type", _MISSING), raw.get("proxy_type", _MISSING), default=StaticProxySettings().type),
                "host": _first_defined(proxy_static_section.get("host", _MISSING), raw.get("proxy_host", _MISSING), default=StaticProxySettings().host),
                "port": _first_defined(proxy_static_section.get("port", _MISSING), raw.get("proxy_port", _MISSING), default=StaticProxySettings().port),
                "username": _first_defined(proxy_static_section.get("username", _MISSING), raw.get("proxy_username", _MISSING), default=StaticProxySettings().username),
                "password": _first_defined(proxy_static_section.get("password", _MISSING), raw.get("proxy_password", _MISSING), default=""),
            },
            "policy": {
                "registration": _first_defined(proxy_policy_section.get("registration", _MISSING), default=ProxyPolicy().registration),
                "account_validate": _first_defined(proxy_policy_section.get("account_validate", _MISSING), default=ProxyPolicy().account_validate),
                "token_refresh": _first_defined(proxy_policy_section.get("token_refresh", _MISSING), default=ProxyPolicy().token_refresh),
                "cpa_upload": _first_defined(proxy_policy_section.get("cpa_upload", _MISSING), default=ProxyPolicy().cpa_upload),
                "cpa_test": _first_defined(proxy_policy_section.get("cpa_test", _MISSING), default=ProxyPolicy().cpa_test),
            },
            "dynamic": {
                "enabled": _first_defined(proxy_dynamic_section.get("enabled", _MISSING), default=DynamicProxySettings().enabled),
                "api_url": _first_defined(proxy_dynamic_section.get("api_url", _MISSING), default=DynamicProxySettings().api_url),
                "api_key": _first_defined(proxy_dynamic_section.get("api_key", _MISSING), default=""),
                "api_key_header": _first_defined(proxy_dynamic_section.get("api_key_header", _MISSING), default=DynamicProxySettings().api_key_header),
                "result_field": _first_defined(proxy_dynamic_section.get("result_field", _MISSING), default=DynamicProxySettings().result_field),
            },
        },
        "mail": {
            "tempmail": {
                "base_url": _first_defined(tempmail_section.get("base_url", _MISSING), raw.get("tempmail_base_url", _MISSING), default=TempmailSettings().base_url),
                "timeout": _first_defined(tempmail_section.get("timeout", _MISSING), raw.get("tempmail_timeout", _MISSING), default=TempmailSettings().timeout),
                "max_retries": _first_defined(tempmail_section.get("max_retries", _MISSING), raw.get("tempmail_max_retries", _MISSING), default=TempmailSettings().max_retries),
            },
            "custom_domain": {
                "base_url": _first_defined(custom_domain_section.get("base_url", _MISSING), raw.get("custom_domain_base_url", _MISSING), default=CustomDomainMailSettings().base_url),
                "api_key": _first_defined(custom_domain_section.get("api_key", _MISSING), raw.get("custom_domain_api_key", _MISSING), default=""),
            },
            "verification": {
                "code_timeout": _first_defined(verification_section.get("code_timeout", _MISSING), raw.get("email_code_timeout", _MISSING), default=VerificationMailSettings().code_timeout),
                "code_poll_interval": _first_defined(verification_section.get("code_poll_interval", _MISSING), raw.get("email_code_poll_interval", _MISSING), default=VerificationMailSettings().code_poll_interval),
            },
            "outlook": {
                "provider_priority": _first_defined(outlook_section.get("provider_priority", _MISSING), raw.get("outlook_provider_priority", _MISSING), default=OutlookMailSettings().provider_priority),
                "health_failure_threshold": _first_defined(outlook_section.get("health_failure_threshold", _MISSING), raw.get("outlook_health_failure_threshold", _MISSING), default=OutlookMailSettings().health_failure_threshold),
                "health_disable_duration": _first_defined(outlook_section.get("health_disable_duration", _MISSING), raw.get("outlook_health_disable_duration", _MISSING), default=OutlookMailSettings().health_disable_duration),
                "default_client_id": _first_defined(outlook_section.get("default_client_id", _MISSING), raw.get("outlook_default_client_id", _MISSING), default=OutlookMailSettings().default_client_id),
            },
        },
        "cpa": {
            "enabled": _first_defined(cpa_section.get("enabled", _MISSING), raw.get("cpa_enabled", _MISSING), default=CpaSettings().enabled),
            "api_url": _first_defined(cpa_section.get("api_url", _MISSING), raw.get("cpa_api_url", _MISSING), default=CpaSettings().api_url),
            "api_token": _first_defined(cpa_section.get("api_token", _MISSING), raw.get("cpa_api_token", _MISSING), default=""),
            "local_files": {
                "enabled": _first_defined(cpa_local_files_section.get("enabled", _MISSING), default=CpaLocalFilesSettings().enabled),
                "path": _first_defined(cpa_local_files_section.get("path", _MISSING), cpa_local_files_section.get("directory", _MISSING), default=CpaLocalFilesSettings().path),
                "trash_dir": _first_defined(cpa_local_files_section.get("trash_dir", _MISSING), cpa_local_files_section.get("trash_path", _MISSING), default=CpaLocalFilesSettings().trash_dir),
            },
        },
    }


def init_default_settings() -> None:
    config_path = get_config_path()
    if config_path.exists():
        return
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(_settings_to_json_dict(_default_settings()), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _load_settings_from_file() -> Settings:
    init_default_settings()
    config_path = get_config_path()
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    defaults = _settings_to_json_dict(_default_settings())
    normalized = _normalize_config_shape(raw)
    merged = _deep_merge(defaults, normalized)

    env_url = os.environ.get("APP_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if env_url:
        merged["runtime"]["database_url"] = env_url

    return Settings(**merged)


def _save_settings_to_file(settings: Settings) -> None:
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(_settings_to_json_dict(settings), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = _load_settings_from_file()
    return _settings


def update_settings(**kwargs) -> Settings:
    global _settings
    merged = _deep_merge(read_raw_config(), _normalize_config_shape(kwargs))
    updated = Settings(**merged)
    _save_settings_to_file(updated)
    _settings = updated
    return _settings


def get_database_url() -> str:
    settings = get_settings()
    url = settings.database_url
    if url.startswith("sqlite:///"):
        path = url[10:]
        if not os.path.isabs(path):
            abs_path = (get_project_root() / path).resolve()
            return f"sqlite:///{abs_path}"
    return url


def read_raw_config() -> dict[str, Any]:
    init_default_settings()
    raw = json.loads(get_config_path().read_text(encoding="utf-8"))
    defaults = _settings_to_json_dict(_default_settings())
    return _deep_merge(defaults, _normalize_config_shape(raw))


def write_raw_config(payload: dict[str, Any]) -> Settings:
    global _settings
    merged = _deep_merge(read_raw_config(), _normalize_config_shape(payload))
    settings = Settings(**merged)
    _save_settings_to_file(settings)
    _settings = settings
    return settings
