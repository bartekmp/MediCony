"""
Tests for the remove_watch command handler in the bot module.

This module tests the functionality of the remove_watch command handler, which allows
users to delete existing watch configurations through a Telegram bot command.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.bot.commands.watch_remove import register_remove_watch_handler
from tests.utils import DummyMessage, create_mock_fsm_context, setup_command_handler


@pytest.mark.asyncio
async def test_remove_watch_success() -> None:
    """
    Test successful removal of a watch through the remove_watch command.

    This test verifies that when a valid watch ID is provided, the watch
    is successfully removed and a confirmation message is shown.
    """
    # Arrange
    state = create_mock_fsm_context()

    watches = [MagicMock(id=1), MagicMock(id=2)]
    watch_service = MagicMock()
    watch_service.get_all_watches = AsyncMock(return_value=watches)
    watch_service.remove_watch = MagicMock(return_value=True)

    _, router = setup_command_handler(register_remove_watch_handler, watch_service)

    # Act - Start remove command
    msg = DummyMessage("/watch_remove")
    await router.message.handlers[0].callback(msg, state)

    # Assert - Should show watches and ask for ID
    assert any("Choose a watch to remove" in t[0] for t in msg.answered), "Should prompt user to choose a watch"

    # Act - Simulate choosing ID 1
    msg = DummyMessage("1")
    state.get_data = AsyncMock(return_value={"watches": [{"id": 1}, {"id": 2}]})
    await router.message.handlers[1].callback(msg, state)

    # Assert - Should show success message
    assert any("removed successfully" in t[0] for t in msg.answered), "Should show success message"
    assert watch_service.remove_watch.called, "Watch service should be called to remove the watch"


@pytest.mark.asyncio
async def test_remove_watch_abort() -> None:
    """
    Test aborting the remove_watch command.

    This test verifies that when the user chooses to abort the operation,
    no watch is removed and an appropriate message is shown.
    """
    # Arrange
    state = create_mock_fsm_context({"watches": [{"id": 1}]})

    watches = [MagicMock(id=1)]
    watch_service = MagicMock()
    watch_service.get_all_watches = AsyncMock(return_value=watches)
    watch_service.remove_watch = MagicMock()

    _, router = setup_command_handler(register_remove_watch_handler, watch_service)

    # Act - Start remove command
    msg = DummyMessage("/watch_remove")
    await router.message.handlers[0].callback(msg, state)

    # Act - Simulate abort
    msg = DummyMessage("🚫 Abort")
    await router.message.handlers[1].callback(msg, state)

    # Assert
    assert any("aborted" in t[0].lower() for t in msg.answered), "Should show abort message"
    assert not watch_service.remove_watch.called, "Watch service should not be called when aborted"


@pytest.mark.asyncio
async def test_remove_watch_invalid_id() -> None:
    """
    Test removing a watch with an invalid ID.

    This test verifies that when an invalid watch ID is provided,
    an error message is shown and no watch is removed.
    """
    # Arrange
    state = create_mock_fsm_context({"watches": [{"id": 1}, {"id": 2}]})

    watches = [MagicMock(id=1), MagicMock(id=2)]
    watch_service = MagicMock()
    watch_service.get_all_watches = AsyncMock(return_value=watches)
    watch_service.remove_watch = MagicMock()

    _, router = setup_command_handler(register_remove_watch_handler, watch_service)

    # Act - Start remove command
    msg = DummyMessage("/watch_remove")
    await router.message.handlers[0].callback(msg, state)

    # Act - Simulate invalid ID
    msg = DummyMessage("999")
    await router.message.handlers[1].callback(msg, state)

    # Assert
    assert any("invalid watch id" in t[0].lower() for t in msg.answered), "Should show invalid ID error message"
    assert not watch_service.remove_watch.called, "Watch service should not be called with invalid ID"
