from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.medicover.auth import Authenticator


@pytest.fixture
def authenticator():
    with patch("src.medicover.auth.UserAgent") as mock_user_agent:
        mock_user_agent.return_value.random = "test-agent"
        instance = Authenticator("test_user:test_password")
    instance.session = MagicMock()
    return instance


@pytest.mark.asyncio
async def test_skip_mfa_gate_returns_none_when_gate_not_present(authenticator):
    mfa_page_response = MagicMock()
    mfa_page_response.text = "<html><body>No MFA gate here</body></html>"
    authenticator.slack_get = AsyncMock(return_value=mfa_page_response)

    result = await authenticator.skip_mfa_gate("/Account/MfaGate?ReturnUrl=%2Fconnect%2Fauthorize%2Fcallback")

    assert result is None
    authenticator.session.post.assert_not_called()


@pytest.mark.asyncio
async def test_skip_mfa_gate_posts_expected_payload(authenticator):
    mfa_page_response = MagicMock()
    mfa_page_response.text = """
    <html>
      <body>
        <form method=\"post\">
          <input type=\"hidden\" name=\"Input.ReturnUrl\" value=\"/connect/authorize/callback?client_id=web\" />
          <input type=\"hidden\" name=\"__RequestVerificationToken\" value=\"csrf-token-123\" />
          <button formaction=\"/Account/MfaGate?handler=SkipMfaGate\">Skip</button>
        </form>
      </body>
    </html>
    """
    authenticator.slack_get = AsyncMock(return_value=mfa_page_response)

    skip_response = MagicMock()
    skip_response.status_code = 302
    skip_response.headers = {"Location": "/connect/authorize/callback?code=test-auth-code"}
    authenticator.session.post.return_value = skip_response

    result = await authenticator.skip_mfa_gate("/Account/MfaGate?ReturnUrl=%2Fconnect%2Fauthorize%2Fcallback")

    assert result == "/connect/authorize/callback?code=test-auth-code"
    authenticator.session.post.assert_called_once()

    called_url = authenticator.session.post.call_args.args[0]
    called_data = authenticator.session.post.call_args.kwargs["data"]
    called_headers = authenticator.session.post.call_args.kwargs["headers"]

    assert called_url == "https://login-online24.medicover.pl/Account/MfaGate?handler=SkipMfaGate"
    assert called_data == {
        "Input.ReturnUrl": "/connect/authorize/callback?client_id=web",
        "__RequestVerificationToken": "csrf-token-123",
    }
    assert called_headers["Referer"].startswith("https://login-online24.medicover.pl/Account/MfaGate")


@pytest.mark.asyncio
async def test_skip_mfa_gate_raises_when_required_fields_missing(authenticator):
    mfa_page_response = MagicMock()
    mfa_page_response.text = """
    <html>
      <body>
        <form method=\"post\">
          <button formaction=\"/Account/MfaGate?handler=SkipMfaGate\">Skip</button>
        </form>
      </body>
    </html>
    """
    authenticator.slack_get = AsyncMock(return_value=mfa_page_response)

    with pytest.raises(ValueError, match="Failed to extract MFA form fields"):
        await authenticator.skip_mfa_gate("/Account/MfaGate?ReturnUrl=%2Fconnect%2Fauthorize%2Fcallback")
