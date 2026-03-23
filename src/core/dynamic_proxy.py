"""Dynamic proxy helpers."""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from curl_cffi import requests as cffi_requests

logger = logging.getLogger(__name__)


def fetch_dynamic_proxy(
    api_url: str,
    api_key: str = "",
    api_key_header: str = "X-API-Key",
    result_field: str = "",
) -> Optional[str]:
    try:
        headers = {}
        if api_key:
            headers[api_key_header] = api_key

        response = cffi_requests.get(
            api_url,
            headers=headers,
            timeout=10,
            impersonate="chrome110",
        )
        if response.status_code != 200:
            logger.warning("dynamic proxy API returned HTTP %s", response.status_code)
            return None

        text = response.text.strip()
        proxy_url: str | None = None
        if result_field or text.startswith("{") or text.startswith("["):
            try:
                data = json.loads(text)
                if result_field:
                    for key in result_field.split("."):
                        if isinstance(data, dict):
                            data = data.get(key)
                        elif isinstance(data, list) and key.isdigit():
                            data = data[int(key)]
                        else:
                            data = None
                        if data is None:
                            break
                    proxy_url = str(data).strip() if data is not None else None
                elif isinstance(data, dict):
                    for key in ("proxy", "url", "proxy_url", "data", "ip"):
                        value = data.get(key)
                        if value:
                            proxy_url = str(value).strip()
                            break
                if not proxy_url:
                    proxy_url = text
            except ValueError:
                proxy_url = text
        else:
            proxy_url = text

        if not proxy_url:
            logger.warning("dynamic proxy API returned an empty value")
            return None

        if not re.match(r"^(http|socks5)://", proxy_url):
            proxy_url = "http://" + proxy_url

        logger.info("dynamic proxy resolved")
        return proxy_url
    except Exception as exc:
        logger.error("failed to fetch dynamic proxy: %s", exc)
        return None


def get_proxy_url_for_task() -> Optional[str]:
    from ..config.settings import get_settings

    settings = get_settings()
    if settings.proxy_dynamic.enabled and settings.proxy_dynamic.api_url:
        proxy_url = fetch_dynamic_proxy(
            api_url=settings.proxy_dynamic.api_url,
            api_key=settings.proxy_dynamic.api_key.get_secret_value(),
            api_key_header=settings.proxy_dynamic.api_key_header,
            result_field=settings.proxy_dynamic.result_field,
        )
        if proxy_url:
            return proxy_url

    return settings.proxy_url
