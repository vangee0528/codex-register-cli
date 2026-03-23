"""File-backed application settings for the CLI-first build."""

from __future__ import annotations

import json
import os
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


class DefaultSelections(BaseModel):
    email_service_type: str = "tempmail"
    email_service_id: int | None = None
    proxy_id: int | None = None
    cpa_service_id: int | None = None


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


class Settings(BaseModel):
    app_name: str = "OpenAI/Codex CLI registration system"
    app_version: str = "2.1.0"
    debug: bool = False
    database_url: str = "data/database.db"
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    log_retention_days: int = 30
    openai_client_id: str = "app_EMoamEEZ73f0CkXaXp7hrann"
    openai_auth_url: str = "https://auth.openai.com/oauth/authorize"
    openai_token_url: str = "https://auth.openai.com/oauth/token"
    openai_redirect_uri: str = "http://localhost:1455/auth/callback"
    openai_scope: str = "openid email profile offline_access"
    proxy_enabled: bool = False
    proxy_type: str = "http"
    proxy_host: str = "127.0.0.1"
    proxy_port: int = 7890
    proxy_username: str = ""
    proxy_password: SecretStr = SecretStr("")
    registration_max_retries: int = 3
    registration_timeout: int = 120
    registration_default_password_length: int = 12
    registration_sleep_min: int = 5
    registration_sleep_max: int = 30
    tempmail_base_url: str = "https://api.tempmail.lol/v2"
    tempmail_timeout: int = 30
    tempmail_max_retries: int = 3
    custom_domain_base_url: str = ""
    custom_domain_api_key: SecretStr = SecretStr("")
    cpa_enabled: bool = False
    cpa_api_url: str = ""
    cpa_api_token: SecretStr = SecretStr("")
    email_code_timeout: int = 120
    email_code_poll_interval: int = 3
    outlook_provider_priority: List[str] = Field(default_factory=lambda: ["imap_old", "imap_new", "graph_api"])
    outlook_health_failure_threshold: int = 5
    outlook_health_disable_duration: int = 60
    outlook_default_client_id: str = "24d9a0ed-8787-4584-883c-2fd79308940a"
    config_ui_host: str = "127.0.0.1"
    config_ui_port: int = 8765
    defaults: DefaultSelections = Field(default_factory=DefaultSelections)
    registration: RegistrationDefaults = Field(default_factory=RegistrationDefaults)
    workflow: WorkflowDefaults = Field(default_factory=WorkflowDefaults)
    proxy_policy: ProxyPolicy = Field(default_factory=ProxyPolicy)
    proxy_dynamic: DynamicProxySettings = Field(default_factory=DynamicProxySettings)
    proxies: List[ProxyResource] = Field(default_factory=list)
    email_services: List[EmailServiceResource] = Field(default_factory=list)
    cpa_services: List[CpaServiceResource] = Field(default_factory=list)

    @field_validator("database_url", mode="before")
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
    def proxy_url(self) -> Optional[str]:
        if not self.proxy_enabled or not self.proxy_host or not self.proxy_port:
            return None
        auth = ""
        password = self.proxy_password.get_secret_value()
        if self.proxy_username and password:
            auth = f"{self.proxy_username}:{password}@"
        return f"{self.proxy_type}://{auth}{self.proxy_host}:{self.proxy_port}"


_settings: Optional[Settings] = None


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_config_path() -> Path:
    configured = os.environ.get("APP_CONFIG_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return get_project_root() / "config.json"


def _default_settings() -> Settings:
    env_url = os.environ.get("APP_DATABASE_URL") or os.environ.get("DATABASE_URL")
    settings = Settings()
    if env_url:
        settings.database_url = Settings.validate_database_url(env_url)
    return settings


def _settings_to_json_dict(settings: Settings) -> dict[str, Any]:
    data = settings.model_dump()
    data["proxy_password"] = settings.proxy_password.get_secret_value()
    data["custom_domain_api_key"] = settings.custom_domain_api_key.get_secret_value()
    data["cpa_api_token"] = settings.cpa_api_token.get_secret_value()
    data["proxy_dynamic"]["api_key"] = settings.proxy_dynamic.api_key.get_secret_value()
    return data


def _merge_defaults(raw: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(raw)

    defaults_section = normalized.get("defaults") or {}
    normalized["defaults"] = {
        "email_service_type": defaults_section.get("email_service_type") or "tempmail",
        "email_service_id": defaults_section.get("email_service_id"),
        "proxy_id": defaults_section.get("proxy_id"),
        "cpa_service_id": defaults_section.get("cpa_service_id"),
    }

    registration_section = normalized.get("registration") or {}
    normalized["registration"] = {
        "default_count": registration_section.get("default_count", 1),
        "auto_upload_cpa": registration_section.get("auto_upload_cpa", False),
        "save_to_database": registration_section.get("save_to_database", True),
        "service_config": registration_section.get("service_config") or {},
    }

    workflow_section = normalized.get("workflow") or {}
    normalized["workflow"] = {
        "target_account_count": workflow_section.get("target_account_count", 10),
        "refresh_before_validate": workflow_section.get("refresh_before_validate", True),
        "auto_delete_invalid": workflow_section.get("auto_delete_invalid", True),
        "auto_sync_cpa": workflow_section.get("auto_sync_cpa", False),
        "max_registration_attempts": workflow_section.get("max_registration_attempts", 0),
    }

    proxy_policy_section = normalized.get("proxy_policy") or {}
    normalized["proxy_policy"] = {
        "registration": proxy_policy_section.get("registration", True),
        "account_validate": proxy_policy_section.get("account_validate", True),
        "token_refresh": proxy_policy_section.get("token_refresh", True),
        "cpa_upload": proxy_policy_section.get("cpa_upload", False),
        "cpa_test": proxy_policy_section.get("cpa_test", False),
    }

    dynamic_section = normalized.get("proxy_dynamic") or {}
    normalized["proxy_dynamic"] = {
        "enabled": dynamic_section.get("enabled", False),
        "api_url": dynamic_section.get("api_url", ""),
        "api_key": dynamic_section.get("api_key", ""),
        "api_key_header": dynamic_section.get("api_key_header", "X-API-Key"),
        "result_field": dynamic_section.get("result_field", ""),
    }

    return normalized


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
    merged = _merge_defaults({**defaults, **raw})

    env_url = os.environ.get("APP_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if env_url:
        merged["database_url"] = env_url

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
    merged = {**read_raw_config(), **kwargs}
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
    return json.loads(get_config_path().read_text(encoding="utf-8"))


def write_raw_config(payload: dict[str, Any]) -> Settings:
    global _settings
    merged = {**read_raw_config(), **payload}
    settings = Settings(**merged)
    _save_settings_to_file(settings)
    _settings = settings
    return settings
