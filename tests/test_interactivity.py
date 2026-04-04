"""Tests for interactivity detection and early failure logic."""

from unittest.mock import MagicMock, patch

import pytest

from src.app.medicony_app import MediCony
from src.medicover.stdin_mfa_provider import is_interactive


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.is_telegram_enabled = False
    config.medicover_default_account = "default"
    config.get_account.return_value = ("user", "pass")
    return config


@pytest.fixture
def mock_args():
    args = MagicMock()
    args.command = "find-appointment"
    args.account = None
    return args


def test_is_interactive_respects_env_var(monkeypatch):
    """Verify that is_interactive follows the MEDICONY_INTERACTIVE env var."""
    # Test True cases
    for val in ["true", "True", "1", "yes"]:
        monkeypatch.setenv("MEDICONY_INTERACTIVE", val)
        assert is_interactive() is True

    # Test False cases
    for val in ["false", "False", "0", "no"]:
        monkeypatch.setenv("MEDICONY_INTERACTIVE", val)
        assert is_interactive() is False

    # Test fallback to isatty
    monkeypatch.delenv("MEDICONY_INTERACTIVE", raising=False)
    with patch("sys.stdin.isatty", return_value=True):
        assert is_interactive() is True
    with patch("sys.stdin.isatty", return_value=False):
        assert is_interactive() is False


def test_medicony_initialization_fails_when_authentication_impossible(mock_config, mock_args, monkeypatch):
    """MediCony should exit early if both Telegram and interactivity are missing."""
    mock_config.is_telegram_enabled = False
    monkeypatch.setenv("MEDICONY_INTERACTIVE", "false")

    with patch("sys.exit") as mock_exit:
        # We also need to mock MedicoverApp to avoid real DB initialization if possible,
        # but here we just want to see if it triggers the check.
        with patch("src.app.medicony_app.MedicoverApp"), patch("src.app.medicony_app.MedicoverDbClient"):
            MediCony(mock_config, mock_args)
            mock_exit.assert_called_once_with(1)


def test_medicony_initialization_succeeds_when_telegram_enabled(mock_config, mock_args, monkeypatch):
    """MediCony should succeed if Telegram is enabled, even if non-interactive."""
    mock_config.is_telegram_enabled = True
    monkeypatch.setenv("MEDICONY_INTERACTIVE", "false")

    with patch("sys.exit") as mock_exit:
        with patch("src.app.medicony_app.MedicoverApp"), patch("src.app.medicony_app.MedicoverDbClient"):
            MediCony(mock_config, mock_args)
            mock_exit.assert_not_called()


def test_medicony_initialization_succeeds_when_interactive(mock_config, mock_args, monkeypatch):
    """MediCony should succeed if interactive, even if Telegram is disabled."""
    mock_config.is_telegram_enabled = False
    monkeypatch.setenv("MEDICONY_INTERACTIVE", "true")

    with patch("sys.exit") as mock_exit:
        with patch("src.app.medicony_app.MedicoverApp"), patch("src.app.medicony_app.MedicoverDbClient"):
            MediCony(mock_config, mock_args)
            mock_exit.assert_not_called()
