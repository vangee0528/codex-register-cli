"""Core constants for the CLI-only build."""

from __future__ import annotations

import random
from datetime import datetime
from enum import Enum
from typing import Dict


class AccountStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    BANNED = "banned"
    FAILED = "failed"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EmailServiceType(str, Enum):
    TEMPMAIL = "tempmail"
    OUTLOOK = "outlook"
    MOE_MAIL = "moe_mail"
    TEMP_MAIL = "temp_mail"
    DUCK_MAIL = "duck_mail"
    FREEMAIL = "freemail"
    IMAP_MAIL = "imap_mail"


APP_NAME = "Codex CLI registration system"
APP_VERSION = "2.2.0"
APP_DESCRIPTION = "CLI workflow for Codex account registration"

OAUTH_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
OAUTH_AUTH_URL = "https://auth.openai.com/oauth/authorize"
OAUTH_TOKEN_URL = "https://auth.openai.com/oauth/token"
OAUTH_REDIRECT_URI = "http://localhost:1455/auth/callback"
OAUTH_SCOPE = "openid email profile offline_access"

OPENAI_API_ENDPOINTS: Dict[str, str] = {
    "sentinel": "https://sentinel.openai.com/backend-api/sentinel/req",
    "signup": "https://auth.openai.com/api/accounts/authorize/continue",
    "register": "https://auth.openai.com/api/accounts/user/register",
    "password_verify": "https://auth.openai.com/api/accounts/password/verify",
    "send_otp": "https://auth.openai.com/api/accounts/email-otp/send",
    "validate_otp": "https://auth.openai.com/api/accounts/email-otp/validate",
    "create_account": "https://auth.openai.com/api/accounts/create_account",
    "select_workspace": "https://auth.openai.com/api/accounts/workspace/select",
}

OPENAI_PAGE_TYPES: Dict[str, str] = {
    "EMAIL_OTP_VERIFICATION": "email_otp_verification",
    "PASSWORD_REGISTRATION": "create_account_password",
    "LOGIN_PASSWORD": "login_password",
}

OTP_CODE_PATTERN = r"(?<!\d)(\d{6})(?!\d)"
OTP_MAX_ATTEMPTS = 40
OTP_CODE_SIMPLE_PATTERN = OTP_CODE_PATTERN
OTP_CODE_SEMANTIC_PATTERN = r"(?:code\s+is|verification\s+code|验证码)\s*[:：]?\s*(\d{6})"

OPENAI_EMAIL_SENDERS = [
    "noreply@openai.com",
    "no-reply@openai.com",
    "@openai.com",
    ".openai.com",
]

OPENAI_VERIFICATION_KEYWORDS = [
    "verify your email",
    "verification code",
    "your openai code",
    "code is",
    "one-time code",
]

PASSWORD_CHARSET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
DEFAULT_PASSWORD_LENGTH = 12

FIRST_NAMES = [
    "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles",
    "Emma", "Olivia", "Ava", "Isabella", "Sophia", "Mia", "Charlotte", "Amelia", "Harper", "Evelyn",
    "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Jamie", "Avery", "Quinn", "Skyler",
    "Liam", "Noah", "Ethan", "Lucas", "Mason", "Oliver", "Elijah", "Aiden", "Henry", "Sebastian",
    "Grace", "Lily", "Chloe", "Zoey", "Nora", "Aria", "Hazel", "Aurora", "Stella", "Ivy",
]


def generate_random_user_info() -> dict:
    name = random.choice(FIRST_NAMES)
    current_year = datetime.now().year
    birth_year = random.randint(current_year - 45, current_year - 18)
    birth_month = random.randint(1, 12)
    if birth_month in [1, 3, 5, 7, 8, 10, 12]:
        birth_day = random.randint(1, 31)
    elif birth_month in [4, 6, 9, 11]:
        birth_day = random.randint(1, 30)
    else:
        birth_day = random.randint(1, 28)
    return {
        "name": name,
        "birthdate": f"{birth_year}-{birth_month:02d}-{birth_day:02d}",
    }


DEFAULT_USER_INFO = {
    "name": "Neo",
    "birthdate": "2000-02-20",
}

ERROR_MESSAGES = {
    "DATABASE_ERROR": "database operation failed",
    "CONFIG_ERROR": "configuration error",
    "NETWORK_ERROR": "network connection failed",
    "TIMEOUT": "operation timed out",
    "VALIDATION_ERROR": "validation failed",
    "EMAIL_SERVICE_UNAVAILABLE": "email service unavailable",
    "EMAIL_CREATION_FAILED": "email creation failed",
    "OTP_NOT_RECEIVED": "verification code not received",
    "OTP_INVALID": "verification code invalid",
    "OPENAI_AUTH_FAILED": "OpenAI authentication failed",
    "OPENAI_RATE_LIMIT": "OpenAI rate limited the request",
    "OPENAI_CAPTCHA": "captcha required",
    "PROXY_FAILED": "proxy connection failed",
    "PROXY_AUTH_FAILED": "proxy authentication failed",
    "ACCOUNT_NOT_FOUND": "account not found",
    "ACCOUNT_ALREADY_EXISTS": "account already exists",
    "ACCOUNT_INVALID": "account invalid",
    "TASK_NOT_FOUND": "task not found",
    "TASK_ALREADY_RUNNING": "task already running",
    "TASK_CANCELLED": "task cancelled",
}
