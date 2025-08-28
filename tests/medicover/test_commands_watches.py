"""
Tests for the watches command handler in the bot module.

This module tests the functionality of the watches command handler, which allows
users to list their active watches through a Telegram bot command.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.bot.commands.watch_list import register_watches_handler


@pytest.mark.asyncio
async def test_handle_watches_no_watches():
    """Test the watches command when no watches are available."""
    # Arrange
    dp = MagicMock()
    watch_service = MagicMock()
    watch_service.get_all_watches = AsyncMock(return_value=[])
    handler = register_watches_handler(dp, watch_service)

    message = AsyncMock()
    message.text = "/watch_list"
    message.answer = AsyncMock()

    # Act
    await handler(message)

    # Assert
    message.answer.assert_awaited_once()
    assert "No active watches" in message.answer.await_args.kwargs["text"]


@pytest.mark.asyncio
async def test_handle_watches_with_watches(monkeypatch):
    """Test the watches command when active watches are available."""
    # Arrange
    dp = MagicMock()
    watches = ["watch1", "watch2"]
    watch_service = MagicMock()
    watch_service.get_all_watches = AsyncMock(return_value=watches)
    handler = register_watches_handler(dp, watch_service)

    # Patch necessary functions
    monkeypatch.setattr("src.bot.commands.watch_list.format_elements_as_text", lambda w: "watch1\nwatch2")
    monkeypatch.setattr("src.bot.commands.watch_list.is_message_below_max_length", lambda m: True)
    monkeypatch.setattr("src.bot.commands.watch_list.format_single_text_element", lambda t: t)

    message = AsyncMock()
    message.text = "/watch_list"
    message.answer = AsyncMock()

    # Act
    await handler(message)

    # Assert
    message.answer.assert_awaited_once()
    called_args = message.answer.await_args.kwargs["text"]
    assert "Active watches" in called_args
    assert "watch1" in called_args
    assert "watch2" in called_args


@pytest.mark.asyncio
async def test_handle_watches_exception(monkeypatch):
    """Test the watches command when an exception occurs while fetching watches."""
    # Arrange
    dp = MagicMock()
    watch_service = MagicMock()
    watch_service.get_all_watches = AsyncMock(side_effect=Exception("fail"))
    handler = register_watches_handler(dp, watch_service)

    message = AsyncMock()
    message.text = "/watch_list"
    message.answer = AsyncMock()

    # Act
    await handler(message)

    # Assert
    message.answer.assert_awaited_once()
    assert "Error while fetching the watch list." in message.answer.await_args.args[0]
