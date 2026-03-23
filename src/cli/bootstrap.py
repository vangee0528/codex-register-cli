"""Runtime bootstrap helpers for the CLI."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from ..config import settings as settings_module
from ..config.settings import get_settings
from ..core.utils import setup_logging
from ..database import session as session_module
from ..database.init_db import initialize_database


def get_runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def load_dotenv(runtime_root: Path) -> None:
    env_path = runtime_root / ".env"
    if not env_path.exists():
        return

    with env_path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def bootstrap_cli(database_url: str | None = None, log_level: str | None = None):
    runtime_root = get_runtime_root()
    load_dotenv(runtime_root)

    data_dir = runtime_root / "data"
    logs_dir = runtime_root / "logs"
    data_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)

    os.environ.setdefault("APP_DATA_DIR", str(data_dir))
    os.environ.setdefault("APP_LOGS_DIR", str(logs_dir))

    if database_url:
        os.environ["APP_DATABASE_URL"] = database_url

    session_module._db_manager = None
    settings_module._settings = None

    settings = get_settings()
    effective_database_url = database_url or settings.database_url
    initialize_database(effective_database_url)

    effective_log_level = log_level or settings.log_level
    log_file = str(logs_dir / Path(settings.log_file).name)
    setup_logging(log_level=effective_log_level, log_file=log_file)

    logger = logging.getLogger(__name__)
    logger.debug("CLI runtime root: %s", runtime_root)
    logger.debug("CLI data dir: %s", data_dir)
    logger.debug("CLI logs dir: %s", logs_dir)
    return settings
