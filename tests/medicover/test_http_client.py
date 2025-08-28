"""
Tests for the HTTPClient class functionality.

This module tests the HTTP client including authentication, request handling,
re-authentication on 401 errors, and error handling for various HTTP methods.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from src.http_client import HTTPClient
from src.medicover.auth import Authenticator


class TestHTTPClient:
    """Test cases for the HTTPClient class."""

    @pytest.fixture
    def mock_authenticator(self):
        """Create a mock authenticator."""
        authenticator = MagicMock(spec=Authenticator)
        authenticator.login = AsyncMock()
        authenticator.headers = {"Authorization": "Bearer test_token", "User-Agent": "test"}
        return authenticator

    @pytest.fixture
    def http_client(self, mock_authenticator):
        """Create HTTPClient instance with mock authenticator."""
        return HTTPClient(mock_authenticator)

    @pytest.mark.asyncio
    async def test_init(self, mock_authenticator):
        """Test HTTPClient initialization."""
        client = HTTPClient(mock_authenticator)
        assert client.authenticator == mock_authenticator
        assert client.session is not None
        assert client.headers is None

    @pytest.mark.asyncio
    async def test_auth_success(self, http_client, mock_authenticator):
        """Test successful authentication."""
        mock_session = MagicMock()
        mock_authenticator.login.return_value = mock_session

        await http_client.auth()

        mock_authenticator.login.assert_called_once()
        assert http_client.session == mock_session
        assert http_client.headers == mock_authenticator.headers

    @pytest.mark.asyncio
    async def test_auth_with_retries(self, http_client, mock_authenticator):
        """Test authentication with retries on failure."""
        mock_session = MagicMock()
        mock_authenticator.login.side_effect = [
            Exception("Network error"),
            Exception("Another error"),
            mock_session,  # Success on third try
        ]

        await http_client.auth()

        assert mock_authenticator.login.call_count == 3
        assert http_client.session == mock_session

    @pytest.mark.asyncio
    async def test_re_auth(self, http_client, mock_authenticator):
        """Test re-authentication calls auth method."""
        mock_session = MagicMock()
        mock_authenticator.login.return_value = mock_session

        await http_client.re_auth()

        mock_authenticator.login.assert_called_once()
        assert http_client.session == mock_session

    @pytest.mark.asyncio
    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("random.randint", return_value=1)
    async def test_get_success(self, mock_randint, mock_sleep, http_client, mock_authenticator):
        """Test successful GET request."""
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        http_client.session = mock_session
        http_client.headers = {"Authorization": "Bearer test_token"}

        # Execute
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_event_loop = MagicMock()
            mock_loop.return_value = mock_event_loop
            mock_event_loop.run_in_executor = AsyncMock(return_value=mock_response)

            result = await http_client.get("https://test.com", {"param": "value"})

        # Verify
        assert result == mock_response
        mock_sleep.assert_called_once_with(1)
        mock_event_loop.run_in_executor.assert_called_once()

    @pytest.mark.asyncio
    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("random.randint", return_value=1)
    async def test_get_401_triggers_reauth(self, mock_randint, mock_sleep, http_client, mock_authenticator):
        """Test that 401 response triggers re-authentication and retry."""
        # Setup first response (401)
        mock_response_401 = MagicMock()
        mock_response_401.status_code = 401

        # Setup second response (success after reauth)
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.raise_for_status.return_value = None

        mock_session = MagicMock()
        http_client.session = mock_session
        http_client.headers = {"Authorization": "Bearer test_token"}

        # Mock authenticator for re-auth
        mock_authenticator.login.return_value = mock_session

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_event_loop = MagicMock()
            mock_loop.return_value = mock_event_loop
            # First call returns 401, subsequent calls should raise RuntimeError for retry
            mock_event_loop.run_in_executor = AsyncMock(
                side_effect=[
                    mock_response_401,
                    RuntimeError("Re-authenticated after 401, retrying request"),
                    mock_response_200,
                ]
            )

            result = await http_client.get("https://test.com", {"param": "value"})

        # Verify re-authentication was called
        mock_authenticator.login.assert_called_once()
        assert result == mock_response_200

    @pytest.mark.asyncio
    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("random.randint", return_value=1)
    async def test_get_connection_error_retry(self, mock_randint, mock_sleep, http_client):
        """Test that connection errors trigger retries."""
        mock_session = MagicMock()
        http_client.session = mock_session
        http_client.headers = {"Authorization": "Bearer test_token"}

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_event_loop = MagicMock()
            mock_loop.return_value = mock_event_loop
            # First two calls raise ConnectionError, third succeeds
            mock_response_success = MagicMock()
            mock_response_success.status_code = 200
            mock_response_success.raise_for_status.return_value = None

            mock_event_loop.run_in_executor = AsyncMock(
                side_effect=[
                    requests.exceptions.ConnectionError("Connection failed"),
                    requests.exceptions.ConnectionError("Connection failed again"),
                    mock_response_success,
                ]
            )

            result = await http_client.get("https://test.com", {"param": "value"})

        assert result == mock_response_success
        assert mock_event_loop.run_in_executor.call_count == 3

    @pytest.mark.asyncio
    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("random.randint", return_value=1)
    async def test_get_max_retries_exceeded(self, mock_randint, mock_sleep, http_client):
        """Test that max retries are respected."""
        mock_session = MagicMock()
        http_client.session = mock_session
        http_client.headers = {"Authorization": "Bearer test_token"}

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_event_loop = MagicMock()
            mock_loop.return_value = mock_event_loop
            # Always raise ConnectionError to exceed max retries
            mock_event_loop.run_in_executor = AsyncMock(
                side_effect=requests.exceptions.ConnectionError("Connection failed")
            )

            with pytest.raises(requests.exceptions.ConnectionError):
                await http_client.get("https://test.com", {"param": "value"})

        # Should attempt 3 times (initial + 2 retries)
        assert mock_event_loop.run_in_executor.call_count == 3

    @pytest.mark.asyncio
    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("random.randint", return_value=1)
    async def test_post_success(self, mock_randint, mock_sleep, http_client):
        """Test successful POST request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}

        mock_session = MagicMock()
        mock_session.post.return_value = mock_response
        http_client.session = mock_session
        http_client.headers = {"Authorization": "Bearer test_token"}

        result = await http_client.post("https://test.com", {"data": "test"})

        assert result == {"success": True}
        mock_sleep.assert_called_once_with(1)
        mock_session.post.assert_called_once_with(
            "https://test.com", headers=http_client.headers, json={"data": "test"}
        )

    @pytest.mark.asyncio
    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("random.randint", return_value=1)
    async def test_post_401_triggers_reauth_and_retry(self, mock_randint, mock_sleep, http_client, mock_authenticator):
        """Test that POST 401 response triggers re-authentication and retry."""
        # Setup responses
        mock_response_401 = MagicMock()
        mock_response_401.status_code = 401

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"success": True}

        mock_session = MagicMock()
        mock_session.post.side_effect = [mock_response_401, mock_response_200]
        http_client.session = mock_session
        http_client.headers = {"Authorization": "Bearer test_token"}

        # Mock re-auth
        mock_authenticator.login.return_value = mock_session

        result = await http_client.post("https://test.com", {"data": "test"})

        assert result == {"success": True}
        assert mock_session.post.call_count == 2
        mock_authenticator.login.assert_called_once()

    @pytest.mark.asyncio
    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("random.randint", return_value=1)
    @patch("src.http_client.log")
    async def test_post_error_status(self, mock_log, mock_randint, mock_sleep, http_client):
        """Test POST request with error status code."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_session = MagicMock()
        mock_session.post.return_value = mock_response
        http_client.session = mock_session
        http_client.headers = {"Authorization": "Bearer test_token"}

        result = await http_client.post("https://test.com", {"data": "test"})

        assert result == {}
        mock_log.error.assert_called_once_with("Error 500: Internal Server Error")

    @pytest.mark.asyncio
    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("random.randint", return_value=1)
    async def test_delete_success(self, mock_randint, mock_sleep, http_client):
        """Test successful DELETE request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"deleted": True}

        mock_session = MagicMock()
        mock_session.delete.return_value = mock_response
        http_client.session = mock_session
        http_client.headers = {"Authorization": "Bearer test_token"}

        result = await http_client.delete("https://test.com/resource/123")

        assert result == {"deleted": True}
        mock_sleep.assert_called_once_with(1)
        mock_session.delete.assert_called_once_with("https://test.com/resource/123", headers=http_client.headers)

    @pytest.mark.asyncio
    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("random.randint", return_value=1)
    async def test_delete_401_triggers_reauth_and_retry(
        self, mock_randint, mock_sleep, http_client, mock_authenticator
    ):
        """Test that DELETE 401 response triggers re-authentication and retry."""
        # Setup responses
        mock_response_401 = MagicMock()
        mock_response_401.status_code = 401

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"deleted": True}

        mock_session = MagicMock()
        mock_session.delete.side_effect = [mock_response_401, mock_response_200]
        http_client.session = mock_session
        http_client.headers = {"Authorization": "Bearer test_token"}

        # Mock re-auth
        mock_authenticator.login.return_value = mock_session

        result = await http_client.delete("https://test.com/resource/123")

        assert result == {"deleted": True}
        assert mock_session.delete.call_count == 2
        mock_authenticator.login.assert_called_once()

    @pytest.mark.asyncio
    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("random.randint", return_value=1)
    @patch("src.http_client.log")
    async def test_delete_error_status(self, mock_log, mock_randint, mock_sleep, http_client):
        """Test DELETE request with error status code."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        mock_session = MagicMock()
        mock_session.delete.return_value = mock_response
        http_client.session = mock_session
        http_client.headers = {"Authorization": "Bearer test_token"}

        result = await http_client.delete("https://test.com/resource/123")

        assert result == {}
        mock_log.error.assert_called_once_with("Error 404: Not Found")

    @pytest.mark.asyncio
    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("random.randint")
    async def test_random_sleep_range(self, mock_randint, mock_sleep, http_client):
        """Test that random sleep is called with correct range."""
        mock_randint.return_value = 2

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}

        mock_session = MagicMock()
        mock_session.post.return_value = mock_response
        http_client.session = mock_session
        http_client.headers = {"Authorization": "Bearer test_token"}

        await http_client.post("https://test.com", {"data": "test"})

        mock_randint.assert_called_with(0, 2)
        mock_sleep.assert_called_once_with(2)

    @pytest.mark.asyncio
    async def test_headers_persistence_after_reauth(self, http_client, mock_authenticator):
        """Test that headers are updated after re-authentication."""
        initial_headers = {"Authorization": "Bearer old_token"}
        new_headers = {"Authorization": "Bearer new_token"}

        http_client.headers = initial_headers
        mock_authenticator.headers = new_headers
        mock_session = MagicMock()
        mock_authenticator.login.return_value = mock_session

        await http_client.re_auth()

        assert http_client.headers == new_headers
        assert http_client.session == mock_session

    @pytest.mark.asyncio
    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("random.randint", return_value=0)
    async def test_zero_sleep_delay(self, mock_randint, mock_sleep, http_client):
        """Test that zero sleep delay works correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}

        mock_session = MagicMock()
        mock_session.post.return_value = mock_response
        http_client.session = mock_session
        http_client.headers = {"Authorization": "Bearer test_token"}

        await http_client.post("https://test.com", {"data": "test"})

        mock_sleep.assert_called_once_with(0)
