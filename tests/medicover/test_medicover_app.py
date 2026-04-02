from unittest.mock import MagicMock
from argparse import Namespace

from src.app.medicover_app import MedicoverApp
from src.config import MediConyConfig


def test_medicover_app_persistence_disabled():
    """Test that session persistence is explicitly disabled if the config defaults to False."""
    args = Namespace(account=None)
    config = MagicMock(spec=MediConyConfig)
    config.medicover_default_account = "default"
    config.medicover_accounts = {"default": ("user", "pass")}
    config.persist_login_sessions = False

    # Mock get_account behavior
    config.get_account.return_value = ("user", "pass")

    db_client_mock = MagicMock()
    # It should not even call get_account_session if persist limit is set to False
    db_client_mock.get_account_session.return_value = ("fake_dev", "fake_ref")

    app = MedicoverApp(config=config, db_client=db_client_mock, args=args)

    # Assert get_account_session was never called
    db_client_mock.get_account_session.assert_not_called()

    # Verify the authenticator attributes are empty
    authenticator = app.api_client._accounts["default"][0]
    assert authenticator.refresh_token is None
    # No save callback should be assigned
    assert authenticator.session_save_callback is None


def test_medicover_app_persistence_enabled():
    """Test that session persistence loads correctly when enabled."""
    args = Namespace(account=None)
    config = MagicMock(spec=MediConyConfig)
    config.medicover_default_account = "default"
    config.medicover_accounts = {"default": ("user", "pass"), "second": ("u2", "p2")}
    config.persist_login_sessions = True

    def mock_get_account(alias):
        return ("user", "pass") if alias == "default" else ("u2", "p2")

    config.get_account.side_effect = mock_get_account

    db_client_mock = MagicMock()

    def mock_db_get_session(alias):
        if alias == "default":
            return ("dev1", "ref1")
        if alias == "second":
            return ("dev2", "ref2")
        return None

    db_client_mock.get_account_session.side_effect = mock_db_get_session

    app = MedicoverApp(config=config, db_client=db_client_mock, args=args)

    # Assert DB was queried for both accounts
    assert db_client_mock.get_account_session.call_count == 2

    auth_default = app.api_client._accounts["default"][0]
    auth_second = app.api_client._accounts["second"][0]

    # Assert the correct tokens were loaded
    assert auth_default.device_id == "dev1"
    assert auth_default.refresh_token == "ref1"
    assert auth_default.session_save_callback is not None

    assert auth_second.device_id == "dev2"
    assert auth_second.refresh_token == "ref2"
    assert auth_second.session_save_callback is not None
