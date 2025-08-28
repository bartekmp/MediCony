"""
Tests for the add_watch command handlers in the bot module.

This module tests the functionality of the add_watch command handlers, which allow
users to create new watch configurations through a Telegram bot conversation.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.fsm.context import FSMContext

from src.bot.commands.watch_add import register_add_watch_handler
from src.config import MediConyConfig
from tests.utils import DummyMessage, create_mock_fsm_context, setup_command_handler


@pytest.mark.asyncio
async def test_add_watch_full_flow():
    """Test the complete flow of adding a new watch with all required inputs."""
    # Arrange - Set up state and mocks
    state = MagicMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    state.clear = AsyncMock()

    # Simulate watch service
    watch_service = MagicMock()
    watch_service.list_available_filters = AsyncMock(
        side_effect=lambda what, **kwargs: [{"id": 1, "value": "A"}, {"id": 2, "value": "B"}]
    )
    watch_service.add_watch = MagicMock()

    # Set up dispatcher and router
    dp = MagicMock()
    dp.sub_routers = []
    # Provide stub config to avoid relying on environment variables
    stub_cfg = MediConyConfig(
        sleep_period_seconds=300,
        medicover_userdata="user:pass",
        telegram_chat_id=None,
        telegram_token=None,
        telegram_add_command_suggested_properties=None,
        log_path="log/medicony.log",
        medicine_search_timeout_seconds=120,
        medicover_accounts={"default": ("user", "pass")},
        medicover_default_account="default",
    )
    router = register_add_watch_handler(dp, watch_service, config=stub_cfg)
    if router not in dp.sub_routers:
        dp.sub_routers.append(router)

    # Act - Simulate user input for each step
    msg = DummyMessage("/watch_add")  # Start command
    await router.message.handlers[0].callback(msg, state)

    msg = DummyMessage("1")  # region
    await router.message.handlers[1].callback(msg, state)

    msg = DummyMessage("CityName")  # city
    await router.message.handlers[2].callback(msg, state)

    msg = DummyMessage("555")  # specialty
    await router.message.handlers[3].callback(msg, state)

    msg = DummyMessage("642")  # doctor
    await router.message.handlers[4].callback(msg, state)
    msg = DummyMessage("9999")  # clinic
    await router.message.handlers[5].callback(msg, state)
    msg = DummyMessage("2025-07-08")  # start_date
    await router.message.handlers[6].callback(msg, state)
    msg = DummyMessage("2025-07-09")  # end_date
    await router.message.handlers[7].callback(msg, state)
    msg = DummyMessage("08:00-16:00")  # time_range
    await router.message.handlers[8].callback(msg, state)
    msg = DummyMessage("yes")  # auto_book
    await router.message.handlers[9].callback(msg, state)
    msg = DummyMessage("doctor:123")  # exclusions
    await router.message.handlers[10].callback(msg, state)
    msg = DummyMessage("Standard")  # type
    await router.message.handlers[11].callback(msg, state)
    # Check that add_watch was called
    assert watch_service.add_watch.called


@pytest.mark.asyncio
async def test_add_watch_abort() -> None:
    """
    Test aborting the add_watch command.

    This test verifies that when the user chooses to abort the operation,
    the state is cleared and the conversation ends.
    """
    # Arrange
    state = create_mock_fsm_context()
    watch_service = MagicMock()
    watch_service.list_available_filters = AsyncMock(return_value=[])
    watch_service.add_watch = MagicMock()

    stub_cfg = MediConyConfig(
        sleep_period_seconds=300,
        medicover_userdata="user:pass",
        telegram_chat_id=None,
        telegram_token=None,
        telegram_add_command_suggested_properties=None,
        log_path="log/medicony.log",
        medicine_search_timeout_seconds=120,
        medicover_accounts={"default": ("user", "pass")},
        medicover_default_account="default",
    )
    _, router = setup_command_handler(register_add_watch_handler, watch_service, config=stub_cfg)

    # Act
    msg = DummyMessage("🚫 Abort")
    await router.message.handlers[1].callback(msg, state)

    # Assert
    assert state.clear.called, "State should be cleared when command is aborted"


@pytest.mark.asyncio
async def test_add_watch_invalid_region() -> None:
    """
    Test providing an invalid region ID in the add_watch command.

    This test verifies that when an invalid region ID is provided,
    an error message is shown and the user is prompted again.
    """
    # Arrange
    state = create_mock_fsm_context()
    watch_service = MagicMock()
    watch_service.list_available_filters = AsyncMock(return_value=[])
    watch_service.add_watch = MagicMock()

    stub_cfg = MediConyConfig(
        sleep_period_seconds=300,
        medicover_userdata="user:pass",
        telegram_chat_id=None,
        telegram_token=None,
        telegram_add_command_suggested_properties=None,
        log_path="log/medicony.log",
        medicine_search_timeout_seconds=120,
        medicover_accounts={"default": ("user", "pass")},
        medicover_default_account="default",
    )
    _, router = setup_command_handler(register_add_watch_handler, watch_service, config=stub_cfg)

    # Act - Simulate invalid region input
    msg = DummyMessage("notanint")
    await router.message.handlers[1].callback(msg, state)

    # Assert
    assert not state.clear.called, "Should not clear state for invalid input"
    assert any("Invalid region" in t[0] for t in msg.answered), "Should show invalid region error message"


@pytest.mark.asyncio
async def test_add_watch_skip_fields():
    state = MagicMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    watch_service = MagicMock()
    watch_service.list_available_filters = AsyncMock(return_value=[{"id": 1, "value": "A"}])
    watch_service.add_watch = MagicMock()
    dp = MagicMock()
    dp.sub_routers = []
    stub_cfg = MediConyConfig(
        sleep_period_seconds=300,
        medicover_userdata="user:pass",
        telegram_chat_id=None,
        telegram_token=None,
        telegram_add_command_suggested_properties=None,
        log_path="log/medicony.log",
        medicine_search_timeout_seconds=120,
        medicover_accounts={"default": ("user", "pass")},
        medicover_default_account="default",
    )
    router = register_add_watch_handler(dp, watch_service, config=stub_cfg)
    if router not in dp.sub_routers:
        dp.sub_routers.append(router)

    # region (required)
    msg = DummyMessage("1")
    await router.message.handlers[1].callback(msg, state)
    # city (skippable)
    msg = DummyMessage("↪️ Skip")
    await router.message.handlers[2].callback(msg, state)
    # specialty (required)
    msg = DummyMessage("555")
    await router.message.handlers[3].callback(msg, state)
    # doctor (skippable)
    msg = DummyMessage("↪️ Skip")
    await router.message.handlers[4].callback(msg, state)
    # clinic (skippable)
    msg = DummyMessage("↪️ Skip")
    await router.message.handlers[5].callback(msg, state)
    # start_date (skippable)
    msg = DummyMessage("↪️ Skip")
    await router.message.handlers[6].callback(msg, state)
    # end_date (skippable)
    msg = DummyMessage("↪️ Skip")
    await router.message.handlers[7].callback(msg, state)
    # time_range (skippable)
    msg = DummyMessage("↪️ Skip")
    await router.message.handlers[8].callback(msg, state)
    # auto_book (skippable)
    msg = DummyMessage("↪️ Skip")
    await router.message.handlers[9].callback(msg, state)
    # exclusions (skippable)
    msg = DummyMessage("↪️ Skip")
    await router.message.handlers[10].callback(msg, state)
    # type (skippable)
    msg = DummyMessage("↪️ Skip")
    await router.message.handlers[11].callback(msg, state)
    assert watch_service.add_watch.called


@pytest.mark.asyncio
async def test_add_watch_suggested_region_city(monkeypatch):
    monkeypatch.setenv("TELEGRAM_ADD_COMMAND_SUGGESTED_PROPERTIES", "region:200;city:Gdańsk")
    state = MagicMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    watch_service = MagicMock()
    watch_service.list_available_filters = AsyncMock(
        side_effect=lambda what, **kwargs: [{"id": 1, "value": "A"}, {"id": 2, "value": "B"}]
    )
    watch_service.add_watch = MagicMock()
    dp = MagicMock()
    dp.sub_routers = []
    stub_cfg = MediConyConfig(
        sleep_period_seconds=300,
        medicover_userdata="user:pass",
        telegram_chat_id=None,
        telegram_token=None,
        telegram_add_command_suggested_properties=None,
        log_path="log/medicony.log",
        medicine_search_timeout_seconds=120,
        medicover_accounts={"default": ("user", "pass")},
        medicover_default_account="default",
    )
    router = register_add_watch_handler(dp, watch_service, config=stub_cfg)
    if router not in dp.sub_routers:
        dp.sub_routers.append(router)
    # Start command
    msg = DummyMessage("/watch_add")
    await router.message.handlers[0].callback(msg, state)
    # Should suggest region 200
    assert any("Suggested choice: *200*" in t[0] for t in msg.answered)
    # Provide region
    msg = DummyMessage("200")
    await router.message.handlers[1].callback(msg, state)
    # Should suggest city Gdańsk
    assert any("Suggested choice: *Gdańsk*" in t[0] for t in msg.answered)
    # Provide city
    msg = DummyMessage("Gdańsk")
    await router.message.handlers[2].callback(msg, state)
    assert any("Available specialties" in t[0] for t in msg.answered)
