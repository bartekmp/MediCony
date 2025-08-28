"""
Tests for the logs command handler in the bot module.

This module tests the functionality of the logs command handler, which allows
users to view recent application logs through the Telegram bot interface.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.bot.commands.logs import register_logs_handler


@pytest.mark.asyncio
async def test_handle_logs_no_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test handling the logs command when no logs are available.

    Verifies that an appropriate message is sent when the log file is empty
    or doesn't exist.

    Args:
        monkeypatch: The pytest monkeypatch fixture.
    """
    # Arrange
    dp = MagicMock()
    # Patch read_n_log_lines_from_file to return empty
    monkeypatch.setattr("src.bot.commands.logs.read_n_log_lines_from_file", lambda: "")
    mock_send = AsyncMock()
    handler = register_logs_handler(dp, send_formatted_reply_override=mock_send)

    message = MagicMock()
    message.text = "/logs"

    # Act
    await handler(message)

    # Assert
    mock_send.assert_awaited_once()
    args, kwargs = mock_send.call_args
    assert "❌ No logs found." in args[2], "Should notify that no logs were found"


@pytest.mark.asyncio
async def test_handle_logs_with_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test handling the logs command when logs are available.

    Verifies that log content is properly formatted and sent when logs exist.

    Args:
        monkeypatch: The pytest monkeypatch fixture.
    """
    # Arrange
    dp = MagicMock()
    mock_send = AsyncMock()
    fake_logs = "line1\nline2\nline3"

    # Patch log reading and formatting functions
    monkeypatch.setattr("src.bot.commands.logs.read_n_log_lines_from_file", lambda: fake_logs)
    monkeypatch.setattr("src.bot.commands.logs.format_code_element", lambda x: f"<code>{x}</code>")

    handler = register_logs_handler(dp, send_formatted_reply_override=mock_send)

    message = MagicMock()
    message.text = "/logs"

    # Act
    await handler(message)

    # Assert
    mock_send.assert_awaited_once()
    args, kwargs = mock_send.call_args
    assert "📜 Last 30 lines of logs:" in args[2], "Should include header indicating logs are being shown"
    assert "<code>line1\nline2\nline3</code>" in args[3], "Should include formatted log content"


@pytest.mark.asyncio
async def test_handle_logs_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test handling the logs command when an exception occurs.

    Verifies that an appropriate error message is sent when an exception
    occurs while trying to fetch logs.

    Args:
        monkeypatch: The pytest monkeypatch fixture.
    """
    # Arrange
    dp = MagicMock()
    mock_send = AsyncMock()

    # Patch read_n_log_lines_from_file to raise an exception
    monkeypatch.setattr(
        "src.bot.commands.logs.read_n_log_lines_from_file", lambda: (_ for _ in ()).throw(Exception("fail"))
    )

    handler = register_logs_handler(dp, send_formatted_reply_override=mock_send)

    message = MagicMock()
    message.text = "/logs"
    message.answer = AsyncMock()  # Patch answer to be awaitable

    # Act
    await handler(message)

    # Assert
    message.answer.assert_awaited_once_with("❌ Error while fetching logs.")
