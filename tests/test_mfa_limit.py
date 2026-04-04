import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from src.medicover.auth import Authenticator, LoginError, MfaLimitExceededError
from src.http_client import HTTPClient


@pytest.fixture
def authenticator():
    auth = Authenticator("user:pass")
    auth.session = requests.Session()
    auth.mfa_code_provider = AsyncMock(return_value="123456")
    return auth


@pytest.mark.asyncio
async def test_handle_mfa_verification_detects_limit_polish(authenticator):
    """Verify that the Polish limit exceeded message is detected."""
    mfa_redirect_url = "/Account/Mfa"

    mock_response = MagicMock()
    mock_response.text = "Przekroczyłeś limit wysyłki kodów jednorazowych. Proszę spróbować później."
    mock_response.status_code = 200

    with patch.object(authenticator, "slack_get", return_value=mock_response):
        with pytest.raises(MfaLimitExceededError, match="Medicover MFA code limit exceeded"):
            await authenticator.handle_mfa_verification(mfa_redirect_url)


@pytest.mark.asyncio
async def test_handle_mfa_verification_detects_limit_english(authenticator):
    """Verify that the English limit exceeded message is detected."""
    mfa_redirect_url = "/Account/Mfa"

    mock_response = MagicMock()
    mock_response.text = "You have exceeded the verification code number limit. Please try again later."
    mock_response.status_code = 200

    with patch.object(authenticator, "slack_get", return_value=mock_response):
        with pytest.raises(MfaLimitExceededError, match="Medicover MFA code limit exceeded"):
            await authenticator.handle_mfa_verification(mfa_redirect_url)


@pytest.mark.asyncio
async def test_login_sets_cooldown_on_limit_error(authenticator):
    """Verify that login sets a 1-hour cooldown when a limit error occurs."""
    # Mocking retrieval of app version and initial authorize call
    authenticator.retrieve_app_version = AsyncMock(return_value="1.0.0")

    mock_auth_response = MagicMock()
    mock_auth_response.status_code = 302
    mock_auth_response.headers = {"Location": "/redirect"}

    mock_form_response = MagicMock()
    mock_form_response.content = b'<input name="__RequestVerificationToken" value="token">'
    mock_form_response.status_code = 200

    mock_login_post_response = MagicMock()
    mock_login_post_response.status_code = 302
    mock_login_post_response.headers = {"Location": "/Account/Mfa"}

    # This is the call that will trigger handle_mfa_verification
    with patch.object(authenticator, "slack_get") as mock_get:
        mock_get.side_effect = [mock_auth_response, mock_form_response]

        with patch.object(requests.Session, "post", return_value=mock_login_post_response):
            # Mock handle_mfa_verification to raise the limit error
            with patch.object(
                authenticator, "handle_mfa_verification", side_effect=MfaLimitExceededError("Limit reached")
            ):
                # Set a dummy callback
                authenticator.mfa_result_callback = AsyncMock()

                with pytest.raises(MfaLimitExceededError):
                    await authenticator.login()

                # Cooldown should be set to ~1 hour from now
                assert authenticator.mfa_cooldown_until > time.time() + 3500

                # Verification result callback should be called
                authenticator.mfa_result_callback.assert_called_once_with(False, "Limit reached")


@pytest.mark.asyncio
async def test_login_fails_fast_during_cooldown(authenticator):
    """Verify that login fails immediately if the cooldown is active."""
    import time

    authenticator.mfa_cooldown_until = time.time() + 1800  # 30 minutes left

    with pytest.raises(LoginError, match="MFA cooldown is active"):
        await authenticator.login()


@pytest.mark.asyncio
async def test_http_client_auth_does_not_retry_login_error():
    """Verify that HTTPClient.auth does not retry when a LoginError occurs."""
    mock_auth = MagicMock()
    mock_auth.refresh_token = None
    # Mock login to raise LoginError
    mock_auth.login = AsyncMock(side_effect=LoginError("Cooldown active"))

    client = HTTPClient(mock_auth)

    with pytest.raises(LoginError):
        await client.auth()

    # login should only be called once, not retried 7 times
    assert mock_auth.login.call_count == 1
