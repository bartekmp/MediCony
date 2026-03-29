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


@pytest.mark.asyncio
async def test_skip_mfa_gate_raises_when_skip_redirects_to_root(authenticator):
    """When Medicover's SkipMfaGate handler redirects to '/' instead of the
    OAuth callback, a clear MfaGateError should be raised."""
    mfa_page_response = MagicMock()
    mfa_page_response.text = """
    <html><body>
        <form method="post">
          <input type="hidden" name="Input.ReturnUrl" value="/connect/authorize/callback?client_id=web" />
          <input type="hidden" name="__RequestVerificationToken" value="csrf-token-123" />
          <button x-show="false" formaction="/Account/MfaGate?handler=SkipMfaGate">Skip</button>
        </form>
    </body></html>
    """
    authenticator.slack_get = AsyncMock(return_value=mfa_page_response)

    skip_response = MagicMock()
    skip_response.status_code = 302
    skip_response.headers = {"Location": "/"}
    authenticator.session.post.return_value = skip_response

    from src.medicover.auth import MfaGateError

    with pytest.raises(MfaGateError, match="MFA gate cannot be skipped"):
        await authenticator.skip_mfa_gate("/Account/MfaGate?ReturnUrl=%2Fconnect%2Fauthorize%2Fcallback")


# --- MFA 2FA Verification Tests ---

MFA_PAGE_HTML = """
<html><body>
  <form id="mfaForm" action="/Account/Mfa?ReturnUrl=%2Fconnect%2Fauthorize%2Fcallback" method="post">
    <input type="hidden" name="Input.MfaCodeId" value="test-mfa-code-id" />
    <input type="hidden" name="Input.ReturnUrl" value="/connect/authorize/callback?client_id=web" />
    <input type="hidden" name="Input.DeviceName" value="" />
    <input type="hidden" name="Input.MfaCode" value="" />
    <input type="hidden" name="Input.IsTrustedDevice" value="False" />
    <input type="hidden" name="Input.Channel" value="Email" />
    <input type="hidden" name="Input.Operation" value="SIGN_IN" />
    <button name="Input.Button" value="confirm">Dalej</button>
    <input type="hidden" name="__RequestVerificationToken" value="csrf-mfa-token" />
  </form>
</body></html>
"""


@pytest.mark.asyncio
async def test_handle_mfa_verification_submits_code_and_returns_redirect(authenticator):
    """When a valid 6-digit code is provided, the form is submitted with IsTrustedDevice=True."""
    mfa_page = MagicMock()
    mfa_page.text = MFA_PAGE_HTML
    mfa_page.url = "https://login-online24.medicover.pl/Account/Mfa?ReturnUrl=..."
    authenticator.slack_get = AsyncMock(return_value=mfa_page)

    # Mock the code provider to return a valid code
    authenticator.mfa_code_provider = AsyncMock(return_value="123456")

    # Mock the form submission response (302 redirect to callback)
    submit_response = MagicMock()
    submit_response.status_code = 302
    submit_response.headers = {"Location": "/connect/authorize/callback?code=auth-code-here"}
    authenticator.session.post.return_value = submit_response

    result = await authenticator.handle_mfa_verification("/Account/Mfa?ReturnUrl=...&Operation=SIGN_IN")

    assert result == "/connect/authorize/callback?code=auth-code-here"
    authenticator.mfa_code_provider.assert_awaited_once_with("Email")

    # Verify the submitted data
    call_data = authenticator.session.post.call_args.kwargs["data"]
    assert call_data["Input.MfaCode"] == "123456"
    assert call_data["Input.IsTrustedDevice"] == "True"
    assert call_data["Input.MfaCodeId"] == "test-mfa-code-id"
    assert call_data["Input.Button"] == "confirm"
    assert call_data["Input.Channel"] == "Email"


@pytest.mark.asyncio
async def test_handle_mfa_verification_raises_when_no_provider(authenticator):
    """When no mfa_code_provider is set, a MfaVerificationError is raised."""
    authenticator.mfa_code_provider = None

    from src.medicover.auth import MfaVerificationError

    with pytest.raises(MfaVerificationError, match="no code provider is configured"):
        await authenticator.handle_mfa_verification("/Account/Mfa?ReturnUrl=...")


@pytest.mark.asyncio
async def test_handle_mfa_verification_raises_on_timeout(authenticator):
    """When the provider returns None (timeout), a MfaVerificationError is raised."""
    mfa_page = MagicMock()
    mfa_page.text = MFA_PAGE_HTML
    mfa_page.url = "https://login-online24.medicover.pl/Account/Mfa?ReturnUrl=..."
    authenticator.slack_get = AsyncMock(return_value=mfa_page)

    authenticator.mfa_code_provider = AsyncMock(return_value=None)

    from src.medicover.auth import MfaVerificationError

    with pytest.raises(MfaVerificationError, match="no code was provided"):
        await authenticator.handle_mfa_verification("/Account/Mfa?ReturnUrl=...")


@pytest.mark.asyncio
async def test_handle_mfa_verification_raises_on_invalid_code_format(authenticator):
    """When the user provides a non-6-digit code, a MfaVerificationError is raised."""
    mfa_page = MagicMock()
    mfa_page.text = MFA_PAGE_HTML
    mfa_page.url = "https://login-online24.medicover.pl/Account/Mfa?ReturnUrl=..."
    authenticator.slack_get = AsyncMock(return_value=mfa_page)

    authenticator.mfa_code_provider = AsyncMock(return_value="12345")  # 5 digits

    from src.medicover.auth import MfaVerificationError

    with pytest.raises(MfaVerificationError, match="Invalid MFA code format"):
        await authenticator.handle_mfa_verification("/Account/Mfa?ReturnUrl=...")


@pytest.mark.asyncio
async def test_handle_mfa_verification_raises_on_server_rejection(authenticator):
    """When the server rejects the code (non-302 response), a MfaVerificationError is raised."""
    mfa_page = MagicMock()
    mfa_page.text = MFA_PAGE_HTML
    mfa_page.url = "https://login-online24.medicover.pl/Account/Mfa?ReturnUrl=..."
    authenticator.slack_get = AsyncMock(return_value=mfa_page)

    authenticator.mfa_code_provider = AsyncMock(return_value="123456")

    # Server returns 200 (re-renders the form, meaning wrong code)
    submit_response = MagicMock()
    submit_response.status_code = 200
    submit_response.text = "<html>Wrong code</html>"
    authenticator.session.post.return_value = submit_response

    from src.medicover.auth import MfaVerificationError

    with pytest.raises(MfaVerificationError, match="MFA code verification failed"):
        await authenticator.handle_mfa_verification("/Account/Mfa?ReturnUrl=...")
