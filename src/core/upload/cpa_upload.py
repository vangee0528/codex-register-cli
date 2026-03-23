"""CPA upload helpers."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

from curl_cffi import CurlMime
from curl_cffi import requests as cffi_requests

from ...config.settings import get_settings
from ...database.models import Account
from ...database.session import get_db

logger = logging.getLogger(__name__)


def _normalize_cpa_auth_files_url(api_url: str) -> str:
    normalized = (api_url or "").strip().rstrip("/")
    lower_url = normalized.lower()

    if not normalized:
        return ""
    if lower_url.endswith("/auth-files"):
        return normalized
    if lower_url.endswith("/v0/management") or lower_url.endswith("/management"):
        return f"{normalized}/auth-files"
    if lower_url.endswith("/v0"):
        return f"{normalized}/management/auth-files"
    return f"{normalized}/v0/management/auth-files"


def _build_cpa_headers(api_token: str, content_type: Optional[str] = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {api_token}"}
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def _build_proxies(proxy: str | None) -> dict[str, str] | None:
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


def _extract_cpa_error(response) -> str:
    error_msg = f"upload failed: HTTP {response.status_code}"
    try:
        error_detail = response.json()
        if isinstance(error_detail, dict):
            error_msg = error_detail.get("message", error_msg)
    except Exception:
        error_msg = f"{error_msg} - {response.text[:200]}"
    return error_msg


def _post_cpa_auth_file_multipart(
    upload_url: str,
    filename: str,
    file_content: bytes,
    api_token: str,
    proxy: str | None,
):
    mime = CurlMime()
    mime.addpart(
        name="file",
        data=file_content,
        filename=filename,
        content_type="application/json",
    )

    return cffi_requests.post(
        upload_url,
        multipart=mime,
        headers=_build_cpa_headers(api_token),
        proxies=_build_proxies(proxy),
        timeout=30,
        impersonate="chrome110",
    )


def _post_cpa_auth_file_raw_json(
    upload_url: str,
    filename: str,
    file_content: bytes,
    api_token: str,
    proxy: str | None,
):
    raw_upload_url = f"{upload_url}?name={quote(filename)}"
    return cffi_requests.post(
        raw_upload_url,
        data=file_content,
        headers=_build_cpa_headers(api_token, content_type="application/json"),
        proxies=_build_proxies(proxy),
        timeout=30,
        impersonate="chrome110",
    )


def generate_token_json(account: Account) -> dict[str, Any]:
    return {
        "type": "codex",
        "email": account.email,
        "expired": account.expires_at.strftime("%Y-%m-%dT%H:%M:%S+08:00") if account.expires_at else "",
        "id_token": account.id_token or "",
        "account_id": account.account_id or "",
        "access_token": account.access_token or "",
        "last_refresh": account.last_refresh.strftime("%Y-%m-%dT%H:%M:%S+08:00") if account.last_refresh else "",
        "refresh_token": account.refresh_token or "",
    }


def upload_to_cpa(
    token_data: dict,
    proxy: str | None = None,
    api_url: str | None = None,
    api_token: str | None = None,
) -> Tuple[bool, str]:
    settings = get_settings()
    effective_url = api_url or settings.cpa_api_url
    effective_token = api_token or (settings.cpa_api_token.get_secret_value() if settings.cpa_api_token else "")

    if not api_url and not settings.cpa_enabled:
        return False, "CPA upload is disabled"
    if not effective_url:
        return False, "CPA API URL is not configured"
    if not effective_token:
        return False, "CPA API token is not configured"

    upload_url = _normalize_cpa_auth_files_url(effective_url)
    filename = f"{token_data['email']}.json"
    file_content = json.dumps(token_data, ensure_ascii=False, indent=2).encode("utf-8")

    try:
        response = _post_cpa_auth_file_multipart(upload_url, filename, file_content, effective_token, proxy)
        if response.status_code in (200, 201):
            return True, "upload succeeded"

        if response.status_code in (404, 405, 415):
            logger.warning("CPA multipart upload failed with %s; retrying raw JSON upload", response.status_code)
            fallback_response = _post_cpa_auth_file_raw_json(upload_url, filename, file_content, effective_token, proxy)
            if fallback_response.status_code in (200, 201):
                return True, "upload succeeded"
            response = fallback_response

        return False, _extract_cpa_error(response)
    except Exception as exc:
        logger.error("CPA upload failed: %s", exc)
        return False, f"upload failed: {exc}"


def batch_upload_to_cpa(
    account_ids: List[int],
    proxy: str | None = None,
    api_url: str | None = None,
    api_token: str | None = None,
) -> dict:
    results = {
        "success_count": 0,
        "failed_count": 0,
        "skipped_count": 0,
        "details": [],
    }

    with get_db() as db:
        for account_id in account_ids:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                results["failed_count"] += 1
                results["details"].append({
                    "id": account_id,
                    "email": None,
                    "success": False,
                    "error": "account not found",
                })
                continue

            if not account.access_token:
                results["skipped_count"] += 1
                results["details"].append({
                    "id": account_id,
                    "email": account.email,
                    "success": False,
                    "error": "missing access token",
                })
                continue

            token_data = generate_token_json(account)
            success, message = upload_to_cpa(token_data, proxy=proxy, api_url=api_url, api_token=api_token)

            if success:
                account.cpa_uploaded = True
                account.cpa_uploaded_at = datetime.utcnow()
                db.commit()
                results["success_count"] += 1
                results["details"].append({
                    "id": account_id,
                    "email": account.email,
                    "success": True,
                    "message": message,
                })
            else:
                results["failed_count"] += 1
                results["details"].append({
                    "id": account_id,
                    "email": account.email,
                    "success": False,
                    "error": message,
                })

    return results


def test_cpa_connection(api_url: str, api_token: str, proxy: str | None = None) -> Tuple[bool, str]:
    if not api_url:
        return False, "API URL cannot be empty"
    if not api_token:
        return False, "API token cannot be empty"

    test_url = _normalize_cpa_auth_files_url(api_url)
    headers = _build_cpa_headers(api_token)

    try:
        response = cffi_requests.get(
            test_url,
            headers=headers,
            proxies=_build_proxies(proxy),
            timeout=10,
            impersonate="chrome110",
        )
        if response.status_code == 200:
            return True, "CPA connection succeeded"
        if response.status_code == 401:
            return False, "connected, but API token is invalid"
        if response.status_code == 403:
            return False, "connected, but remote management is unavailable or token has no permission"
        if response.status_code == 404:
            return False, "auth-files endpoint not found; check the configured CPA URL"
        if response.status_code == 503:
            return False, "connected, but the CPA service is temporarily unavailable"
        return False, f"unexpected HTTP status: {response.status_code}"
    except cffi_requests.exceptions.ConnectionError as exc:
        return False, f"failed to connect: {exc}"
    except cffi_requests.exceptions.Timeout:
        return False, "connection timed out"
    except Exception as exc:
        return False, f"connection test failed: {exc}"
