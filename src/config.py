"""
Centralized configuration management for MediCony application.
Handles environment variable loading, validation, and provides type-safe configuration access.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Tuple

from base64 import b64decode


def _decode(b64: str) -> str:
    try:
        return b64decode(b64.encode("utf-8")).decode("utf-8")
    except Exception:
        # Fallback – return raw to avoid hard failure
        return b64


def parse_medicover_accounts(raw: str) -> Tuple[Dict[str, Tuple[str, str]], str]:
    """
    Parse MEDICOVER_USERDATA supporting multiple accounts.

            Supported formats:
                1) username:password                              -> single default account alias 'default'
                2) alias@BASE64(username):BASE64(password)[;...]  -> multi-account

            Separators:
                - Account entries separated by ';'
                - Alias / credential separator: '@' (only)

            Rationale: '@' avoids ambiguity with base64 '=' padding characters.
    The first parsed account becomes the default alias.
    Returns (mapping, default_alias).
    """
    raw = raw.strip()
    accounts: Dict[str, Tuple[str, str]] = {}
    default_alias = "default"

    if not raw:
        return accounts, default_alias

    # Backward compatible single account (no ';' and no '=' before first ':')
    if ";" not in raw and raw.count(":") == 1 and "=" not in raw.split(":")[0]:
        user, pwd = raw.split(":", 1)
        accounts[default_alias] = (user, pwd)
        return accounts, default_alias

    # Multi-account format; split on ';'
    seen_usernames = set()
    for idx, part in enumerate(filter(None, [p.strip() for p in raw.split(";")])):
        if "@" not in part:
            # Fallback attempt: treat as single user:pass chunk - process only the first one
            if part.count(":") == 1:
                user, pwd = part.split(":", 1)
                alias = "default" if idx == 0 else f"account{idx+1}"
                accounts[alias] = (user, pwd)
                default_alias = alias
                # Single account fallback - return immediately, ignore any other parts
                return accounts, default_alias
            continue
        alias, creds = part.split("@", 1)
        if ":" not in creds:
            continue
        u_enc, p_enc = creds.split(":", 1)
        username = _decode(u_enc)
        password = _decode(p_enc)
        # Check for duplicate username
        if username in seen_usernames:
            raise ValueError(f"Duplicate username found: {username}")
        seen_usernames.add(username)
        # Check for duplicate alias
        if alias in accounts:
            raise ValueError(f"Duplicate alias found: {alias}")
        if idx == 0:
            default_alias = alias
        accounts[alias] = (username, password)

    return accounts, default_alias


@dataclass
class MediConyConfig:
    """Centralized configuration class for MediCony application."""

    # Core application settings (required - no defaults first)
    sleep_period_seconds: int
    medicover_userdata: str  # Raw env value (may contain multiple accounts)

    # Telegram settings
    telegram_chat_id: Optional[str]
    telegram_token: Optional[str]
    telegram_add_command_suggested_properties: Optional[str]

    # Application settings
    log_path: str
    medicine_search_timeout_seconds: int

    # Derived / parsed fields (defaults allowed after required fields)
    medicover_accounts: Dict[str, Tuple[str, str]] = field(default_factory=dict)
    medicover_default_account: str = "default"

    @classmethod
    def from_environment(cls) -> "MediConyConfig":
        """Create configuration from environment variables with validation."""
        # Core settings
        sleep_period_seconds = int(os.environ.get("SLEEP_PERIOD_SEC", "300"))
        medicover_userdata = os.environ.get("MEDICOVER_USERDATA", "")
        accounts, default_alias = parse_medicover_accounts(medicover_userdata)

        # Telegram settings
        telegram_chat_id = os.environ.get("MEDICONY_TELEGRAM_CHAT_ID")
        telegram_token = os.environ.get("MEDICONY_TELEGRAM_TOKEN")
        telegram_add_command_suggested_properties = os.environ.get("TELEGRAM_ADD_COMMAND_SUGGESTED_PROPERTIES")

        # Application settings
        log_path = os.environ.get("LOG_PATH", "log/medicony.log")
        medicine_search_timeout_seconds = int(os.environ.get("MEDICINE_SEARCH_TIMEOUT_SEC", "120"))

        config = cls(
            sleep_period_seconds=sleep_period_seconds,
            medicover_userdata=medicover_userdata,
            telegram_chat_id=telegram_chat_id,
            telegram_token=telegram_token,
            telegram_add_command_suggested_properties=telegram_add_command_suggested_properties,
            log_path=log_path,
            medicine_search_timeout_seconds=medicine_search_timeout_seconds,
            medicover_accounts=accounts,
            medicover_default_account=default_alias if accounts else "default",
        )

        config._validate()
        return config

    def _validate(self) -> None:
        """Validate configuration values."""
        if self.sleep_period_seconds <= 0:
            raise ValueError("SLEEP_PERIOD_SEC must be a positive integer")

        if not self.medicover_userdata.strip():
            raise ValueError("MEDICOVER_USERDATA is required and cannot be empty")

        if not self.medicover_accounts:
            raise ValueError(
                "MEDICOVER_USERDATA could not be parsed into at least one account (expected username:password or alias@BASE64USER:BASE64PASS)"
            )

        # Validate that if one Telegram setting is provided, both are provided
        telegram_settings_provided = [self.telegram_chat_id, self.telegram_token]
        if any(telegram_settings_provided) and not all(telegram_settings_provided):
            raise ValueError("Both MEDICONY_TELEGRAM_CHAT_ID and MEDICONY_TELEGRAM_TOKEN must be provided together")

        # Validate log path
        log_dir = Path(self.log_path).parent
        if not log_dir.exists():
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise ValueError(f"Cannot create log directory {log_dir}: {e}")

    @property
    def is_telegram_enabled(self) -> bool:
        """Check if Telegram notifications are properly configured."""
        return bool(
            self.telegram_chat_id
            and self.telegram_token
            and self.telegram_chat_id.strip()
            and self.telegram_token.strip()
        )

    def get_env_info(self) -> dict[str, str]:
        """Get environment information for logging purposes."""
        return {
            "SLEEP_PERIOD_SEC": str(self.sleep_period_seconds),
            "MEDICONY_TELEGRAM_CHAT_ID": "set" if self.telegram_chat_id else "not set",
            "MEDICONY_TELEGRAM_TOKEN": "set" if self.telegram_token else "not set",
            "TELEGRAM_ADD_COMMAND_SUGGESTED_PROPERTIES": (
                str(self.telegram_add_command_suggested_properties)
                if self.telegram_add_command_suggested_properties
                else "not set"
            ),
            "LOG_PATH": self.log_path,
            "MEDICOVER_ACCOUNTS": ",".join(self.medicover_accounts.keys()),
        }

    def get_account(self, alias: Optional[str] = None) -> Tuple[str, str]:
        """Return (username, password) for given alias or default."""
        if not self.medicover_accounts:
            raise ValueError("No Medicover accounts configured")
        if alias is None:
            alias = self.medicover_default_account
        if alias not in self.medicover_accounts:
            raise ValueError(f"Unknown Medicover account alias: {alias}")
        return self.medicover_accounts[alias]

    def list_account_aliases(self) -> list[str]:
        return list(self.medicover_accounts.keys())


# Global configuration instance
_config: Optional[MediConyConfig] = None


def get_config() -> MediConyConfig:
    """Get the global configuration instance, creating it if necessary."""
    global _config
    if _config is None:
        _config = MediConyConfig.from_environment()
    return _config


def reset_config() -> None:
    """Reset the global configuration instance. Mainly used for testing."""
    global _config
    _config = None
