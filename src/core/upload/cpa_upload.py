"""CPA upload helpers."""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

from curl_cffi import CurlMime
from curl_cffi import requests as cffi_requests

from ...config.settings import get_settings
from ...database import crud
from ...database.models import Account
from ...database.session import get_db

logger = logging.getLogger(__name__)
LOCAL_CPA_SYNC_SOURCE = "cpa_sync"
LOCAL_CPA_EMAIL_SERVICE = "cpa_local"


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


def _resolve_local_cpa_base_dir(settings) -> Path | None:
    local_files = settings.cpa.local_files
    if not local_files.enabled:
        return None

    raw_path = (local_files.path or "").strip()
    if not raw_path:
        return None

    candidate = Path(raw_path).expanduser()
    if candidate.suffix.lower() == ".json":
        return candidate.parent
    return candidate


def _resolve_local_cpa_source_path(path_value: str | None, settings) -> Path | None:
    raw_path = (path_value or settings.cpa.local_files.path or "").strip()
    if not raw_path:
        return None
    return Path(raw_path).expanduser()


def _resolve_local_cpa_trash_dir(base_dir: Path, settings) -> Path:
    configured = (settings.cpa.local_files.trash_dir or "").strip()
    if configured:
        return Path(configured).expanduser()
    return base_dir / "_trash"


def _find_local_cpa_auth_files(base_dir: Path, email: str) -> list[Path]:
    expected_name = f"{email}.json"
    direct_match = base_dir / expected_name
    if direct_match.exists():
        return [direct_match]

    if not base_dir.exists() or not base_dir.is_dir():
        return []

    expected_lower = expected_name.lower()
    return [
        candidate
        for candidate in base_dir.glob("*.json")
        if candidate.name.lower() == expected_lower
    ]


def list_local_cpa_auth_files(path_value: str | None, settings) -> tuple[list[Path], str | None]:
    source_path = _resolve_local_cpa_source_path(path_value, settings)
    if source_path is None:
        return [], "local CPA path is not configured"

    if source_path.suffix.lower() == ".json":
        if not source_path.exists() or not source_path.is_file():
            return [], f"local CPA file not found: {source_path}"
        return [source_path], None

    if not source_path.exists() or not source_path.is_dir():
        return [], f"local CPA directory not found: {source_path}"

    return sorted(source_path.glob("*.json")), None


def _parse_cpa_datetime(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None

    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def _normalize_local_cpa_email(payload: dict[str, Any], file_path: Path) -> str:
    email = str(payload.get("email") or "").strip()
    if email:
        return email
    return file_path.stem.strip()


def _account_status_from_expiration(expires_at: datetime | None) -> str:
    if expires_at is None:
        return "active"
    return "active" if expires_at > datetime.utcnow() else "expired"


def sync_accounts_from_local_cpa(
    *,
    settings,
    path_value: str | None = None,
) -> dict[str, Any]:
    files, error = list_local_cpa_auth_files(path_value, settings)
    payload = {
        "source_path": str(_resolve_local_cpa_source_path(path_value, settings) or ""),
        "summary": {
            "scanned_count": len(files),
            "created_count": 0,
            "updated_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
        },
        "details": [],
    }

    if error:
        payload["summary"]["failed_count"] = 1
        payload["details"].append({
            "file": payload["source_path"],
            "email": None,
            "success": False,
            "action": "error",
            "message": error,
            "account_id": None,
        })
        return payload

    if not files:
        return payload

    with get_db() as db:
        for file_path in files:
            try:
                raw_payload = json.loads(file_path.read_text(encoding="utf-8"))
                if not isinstance(raw_payload, dict):
                    raise ValueError("JSON root must be an object")

                email = _normalize_local_cpa_email(raw_payload, file_path)
                if not email:
                    raise ValueError("email is missing")

                expires_at = _parse_cpa_datetime(raw_payload.get("expired"))
                last_refresh = _parse_cpa_datetime(raw_payload.get("last_refresh"))
                status = _account_status_from_expiration(expires_at)
                account = crud.get_account_by_email(db, email)
                imported_at = datetime.utcnow()
                extra_data = {
                    "imported_from": "local_cpa_file",
                    "local_cpa_file": str(file_path),
                    "local_cpa_type": raw_payload.get("type") or "",
                    "last_synced_at": imported_at.isoformat(),
                }

                if account is None:
                    created = crud.create_account(
                        db,
                        email=email,
                        password="",
                        client_id=settings.openai_client_id,
                        email_service=LOCAL_CPA_EMAIL_SERVICE,
                        account_id=raw_payload.get("account_id") or None,
                        access_token=raw_payload.get("access_token") or None,
                        refresh_token=raw_payload.get("refresh_token") or None,
                        id_token=raw_payload.get("id_token") or None,
                        expires_at=expires_at,
                        extra_data=extra_data,
                        status=status,
                        source=LOCAL_CPA_SYNC_SOURCE,
                    )
                    account = crud.update_account(
                        db,
                        created.id,
                        last_refresh=last_refresh,
                        cpa_uploaded=True,
                        cpa_uploaded_at=imported_at,
                    ) or created
                    action = "created"
                    payload["summary"]["created_count"] += 1
                else:
                    merged_extra = dict(account.extra_data or {})
                    merged_extra.update(extra_data)
                    account = crud.update_account(
                        db,
                        account.id,
                        account_id=raw_payload.get("account_id") or None,
                        access_token=raw_payload.get("access_token") or None,
                        refresh_token=raw_payload.get("refresh_token") or None,
                        id_token=raw_payload.get("id_token") or None,
                        expires_at=expires_at,
                        last_refresh=last_refresh,
                        status=status,
                        cpa_uploaded=True,
                        cpa_uploaded_at=imported_at,
                        extra_data=merged_extra,
                    ) or account
                    action = "updated"
                    payload["summary"]["updated_count"] += 1

                payload["details"].append({
                    "file": str(file_path),
                    "email": email,
                    "success": True,
                    "action": action,
                    "message": "synchronized",
                    "account_id": account.id,
                    "status": account.status,
                })
            except Exception as exc:
                payload["summary"]["failed_count"] += 1
                payload["details"].append({
                    "file": str(file_path),
                    "email": None,
                    "success": False,
                    "action": "error",
                    "message": str(exc),
                    "account_id": None,
                })

    return payload


def _unique_trash_target(trash_dir: Path, source: Path) -> Path:
    target = trash_dir / source.name
    if not target.exists():
        return target

    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    counter = 1
    while True:
        candidate = trash_dir / f"{source.stem}.invalid-{stamp}-{counter}{source.suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def cleanup_local_cpa_auth_files(emails: list[str], settings) -> dict[str, Any]:
    results = {
        "enabled": bool(settings.cpa.local_files.enabled),
        "configured_path": settings.cpa.local_files.path,
        "trash_dir": settings.cpa.local_files.trash_dir,
        "moved_count": 0,
        "not_found_count": 0,
        "failed_count": 0,
        "details": [],
    }

    if not emails:
        return results

    base_dir = _resolve_local_cpa_base_dir(settings)
    if base_dir is None:
        for email in emails:
            results["details"].append({
                "email": email,
                "status": "disabled",
                "moved_files": [],
                "error": None,
            })
        return results

    results["resolved_path"] = str(base_dir)

    if not base_dir.exists() or not base_dir.is_dir():
        for email in emails:
            results["failed_count"] += 1
            results["details"].append({
                "email": email,
                "status": "error",
                "moved_files": [],
                "error": f"local CPA auth directory not found: {base_dir}",
            })
        return results

    trash_dir = _resolve_local_cpa_trash_dir(base_dir, settings)
    results["trash_dir"] = str(trash_dir)

    for email in emails:
        matches = _find_local_cpa_auth_files(base_dir, email)
        if not matches:
            results["not_found_count"] += 1
            results["details"].append({
                "email": email,
                "status": "not_found",
                "moved_files": [],
                "error": None,
            })
            continue

        moved_files: list[str] = []
        errors: list[str] = []
        try:
            trash_dir.mkdir(parents=True, exist_ok=True)
            for match in matches:
                target = _unique_trash_target(trash_dir, match)
                shutil.move(str(match), str(target))
                moved_files.append(str(target))
        except Exception as exc:
            errors.append(str(exc))

        if errors:
            results["failed_count"] += 1
            results["details"].append({
                "email": email,
                "status": "error",
                "moved_files": moved_files,
                "error": "; ".join(errors),
            })
            continue

        results["moved_count"] += len(moved_files)
        results["details"].append({
            "email": email,
            "status": "moved",
            "moved_files": moved_files,
            "error": None,
        })

    return results


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
