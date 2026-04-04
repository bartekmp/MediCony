"""Tests for TelegramMfaProvider."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot.mfa_provider import TelegramMfaProvider


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.send_message = AsyncMock()
    return bot


@pytest.fixture
def mock_dispatcher():
    dp = MagicMock()
    dp.include_router = MagicMock()
    return dp


@pytest.fixture
def provider(mock_bot, mock_dispatcher):
    with patch.dict("os.environ", {"MEDICONY_TELEGRAM_CHAT_ID": "12345"}):
        return TelegramMfaProvider(mock_bot, mock_dispatcher)


@pytest.mark.asyncio
async def test_request_code_sends_telegram_message(provider, mock_bot):
    """The provider should send a message via Telegram asking for the code."""
    sent_msg = MagicMock()
    sent_msg.message_id = 42
    mock_bot.send_message.return_value = sent_msg

    # Simulate a concurrent reply that sets the future
    async def fake_send(*args, **kwargs):
        # After sending, simulate a reply arriving
        await asyncio.sleep(0.05)
        if provider._pending_future and not provider._pending_future.done():
            provider._pending_future.set_result("654321")
        return sent_msg

    mock_bot.send_message = fake_send

    result = await provider.request_code("Email")

    assert result == "654321"


@pytest.mark.asyncio
async def test_request_code_returns_none_on_timeout(provider, mock_bot):
    """When the user doesn't reply within the timeout, None is returned."""
    import src.bot.mfa_provider as mfa_mod

    original_timeout = mfa_mod.MFA_TIMEOUT_SECONDS
    mfa_mod.MFA_TIMEOUT_SECONDS = 0.1  # 100ms for fast test

    sent_msg = MagicMock()
    sent_msg.message_id = 42
    mock_bot.send_message.return_value = sent_msg

    try:
        result = await provider.request_code("SMS")
        assert result is None
    finally:
        mfa_mod.MFA_TIMEOUT_SECONDS = original_timeout


@pytest.mark.asyncio
async def test_request_code_returns_none_when_chat_id_missing(mock_bot, mock_dispatcher):
    """When MEDICONY_TELEGRAM_CHAT_ID is not set, None is returned."""
    with patch.dict("os.environ", {}, clear=True):
        p = TelegramMfaProvider(mock_bot, mock_dispatcher)
        result = await p.request_code("Email")
        assert result is None


@pytest.mark.asyncio
async def test_send_verification_result(provider, mock_bot):
    """The provider should send a status message as a reply."""
    provider._mfa_message_id = 42
    await provider.send_verification_result(True)

    mock_bot.send_message.assert_called_once()
    args, kwargs = mock_bot.send_message.call_args
    assert "Verification successful" in kwargs["text"]
    assert kwargs["reply_to_message_id"] == 42
    assert provider._mfa_message_id is None
    assert provider._pending_future is None


@pytest.mark.asyncio
async def test_send_verification_result_failure(provider, mock_bot):
    """The provider should send a failure message with details."""
    provider._mfa_message_id = 42
    await provider.send_verification_result(False, "Invalid code")

    mock_bot.send_message.assert_called_once()
    args, kwargs = mock_bot.send_message.call_args
    assert "Verification failed" in kwargs["text"]
    assert "Invalid code" in kwargs["text"]
    assert kwargs["reply_to_message_id"] == 42
