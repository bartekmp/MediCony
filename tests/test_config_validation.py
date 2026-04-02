"""Tests for config validation, particularly duplicate detection in multi-account parsing."""

import pytest

from src.config import MediConyConfig, parse_medicover_accounts


def test_parse_medicover_accounts_duplicate_alias():
    """Test that duplicate aliases raise ValueError."""
    # Same alias used twice
    userdata = "acc1@dXNlcjE=:cGFzczE=;acc1@dXNlcjI=:cGFzczI="
    with pytest.raises(ValueError, match="Duplicate alias found: acc1"):
        parse_medicover_accounts(userdata)


def test_parse_medicover_accounts_duplicate_username():
    """Test that duplicate usernames raise ValueError."""
    # Same username (user1) encoded twice with different aliases
    userdata = "acc1@dXNlcjE=:cGFzczE=;acc2@dXNlcjE=:cGFzczI="
    with pytest.raises(ValueError, match="Duplicate username found: user1"):
        parse_medicover_accounts(userdata)


def test_parse_medicover_accounts_duplicate_username_fallback():
    """Test that single account fallback processes only first credential, ignoring duplicates."""
    # Fallback format without @ separator - should only process first entry
    userdata = "user1:pass1;user1:pass2"
    accounts, default = parse_medicover_accounts(userdata)

    # Should only have processed the first account
    assert len(accounts) == 1
    assert "default" in accounts
    assert accounts["default"] == ("user1", "pass1")
    assert default == "default"


def test_parse_medicover_accounts_valid_multiple():
    """Test that valid multiple accounts parse correctly."""
    # Different aliases and usernames
    userdata = "acc1@dXNlcjE=:cGFzczE=;acc2@dXNlcjI=:cGFzczI="
    accounts, default = parse_medicover_accounts(userdata)

    assert len(accounts) == 2
    assert "acc1" in accounts
    assert "acc2" in accounts
    assert accounts["acc1"] == ("user1", "pass1")
    assert accounts["acc2"] == ("user2", "pass2")
    assert default == "acc1"


def test_parse_medicover_accounts_fallback_ignores_additional():
    """Test that fallback format only processes first entry and ignores additional ones."""
    userdata = "user1:pass1;extra_entry;another@entry"
    accounts, default = parse_medicover_accounts(userdata)

    # Should only process the first fallback entry
    assert len(accounts) == 1
    assert "default" in accounts
    assert accounts["default"] == ("user1", "pass1")
    assert default == "default"


def test_parse_medicover_accounts_single_account_no_duplicates():
    """Test that single account format doesn't trigger duplicate validation."""
    userdata = "user1:pass1"
    accounts, default = parse_medicover_accounts(userdata)

    assert len(accounts) == 1
    assert "default" in accounts
    assert accounts["default"] == ("user1", "pass1")
    assert default == "default"


@pytest.fixture
def clean_env(monkeypatch):
    """Fixture to ensure environment variables are clean before tests."""
    vars_to_clean = [
        "MEDICONY_PERSIST_LOGIN_SESSIONS",
        "MEDICOVER_USERDATA",
        "SLEEP_PERIOD_SEC",
        "MEDICONY_TELEGRAM_CHAT_ID",
        "MEDICONY_TELEGRAM_TOKEN",
        "LOG_PATH",
        "MEDICINE_SEARCH_TIMEOUT_SECONDS",
        "MEDICONY_ENCRYPTION_KEY",
    ]
    for var in vars_to_clean:
        monkeypatch.delenv(var, raising=False)
    # Required for basic setup
    monkeypatch.setenv("MEDICOVER_USERDATA", "user:pass")


def test_persist_login_sessions_default(clean_env):
    """Test that persist_login_sessions defaults to False."""
    config = MediConyConfig.from_environment()
    assert config.persist_login_sessions is False


@pytest.mark.parametrize(
    "env_val,expected",
    [
        ("0", False),
        ("false", False),
        ("False", False),
        ("1", True),
        ("true", True),
        ("True", True),
        ("yes", True),
        ("random_string", False),
    ],
)
def test_persist_login_sessions_values(clean_env, monkeypatch, env_val, expected):
    """Test that persist_login_sessions maps specific values correctly."""
    monkeypatch.setenv("MEDICONY_PERSIST_LOGIN_SESSIONS", env_val)
    config = MediConyConfig.from_environment()
    assert config.persist_login_sessions is expected
