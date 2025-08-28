"""
Tests for the edit_watch command handlers in the bot module.

This module tests the functionality of the edit_watch command handlers, which allow
users to modify existing watch configurations through a Telegram bot conversation.
"""

import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.bot.commands.watch_edit import EditWatchStates, escape_markdown, register_edit_watch_handler
from src.id_value_util import IdValue
from src.medicover.watch import WatchTimeRange


class DummyIdValue:
    """
    Mock implementation of IdValue for testing purposes.

    This class simulates the behavior of the IdValue class without requiring
    the full implementation.

    Args:
        id: The ID value to use for this mock
        value: The display value (defaults to "Value{id}")
    """

    def __init__(self, id: int, value: Optional[str] = None):
        self.id = id
        self.value = value or f"Value{id}"


class DummyWatch:
    """
    Mock implementation of Watch class for testing purposes.

    Simulates the Watch dataclass without requiring all the validation logic.
    Provides just enough functionality to test the edit_watch handlers.

    Args:
        id: The watch ID
        city: The city name
        clinic: The clinic ID value object
        start_date: The start date for the watch
        end_date: The end date for the watch (optional)
        time_range: The time range for the watch (optional)
        exclusions: Dictionary of exclusions (optional)
        auto_book: Whether to automatically book appointments (default: False)
    """

    def __init__(
        self,
        id: int,
        city: str = "",
        clinic: Any = None,
        start_date: datetime.date = datetime.date.min,
        end_date: Optional[datetime.date] = None,
        time_range: Optional[WatchTimeRange] = None,
        exclusions: Optional[Dict[str, List[str]]] = None,
        auto_book: bool = False,
    ):
        self.id = id
        self.city = city
        self.clinic = clinic
        self.start_date = start_date
        self.end_date = end_date
        self.time_range = time_range or WatchTimeRange("00:00:00")
        self.exclusions = exclusions
        self.auto_book = auto_book

        # Add required fields from Watch dataclass that tests might rely on
        self.region = IdValue(1, "Region1")
        self.specialty = [IdValue(1, "Specialty1")]
        self.doctor = None
        self.type = "Standard"


# Helper functions for testing
def get_watch_by_id(watches: List[DummyWatch], id_: str) -> Optional[DummyWatch]:
    """
    Find a watch by its ID in a collection of watches.

    Args:
        watches: A sequence of DummyWatch objects
        id_: The ID to search for, as a string

    Returns:
        The matching watch or None if not found
    """
    for w in watches:
        if str(w.id) == id_:
            return w
    return None


def get_changed_fields(old: DummyWatch, new: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare an old DummyWatch object with new values from a dictionary.

    This is a patched version of the original get_changed_fields function
    that works with DummyWatch objects instead of Watch dataclasses.

    Args:
        old: The original DummyWatch object
        new: Dictionary containing the new values to compare against

    Returns:
        A dictionary of fields that have changed and their new values
    """
    changed = {}
    for k, v in new.items():
        if v is None:
            continue
        # Handle IdValue fields
        if k == "clinic_id" and hasattr(old, "clinic"):
            old_id = getattr(old.clinic, "id", None) if old.clinic else None
            if v != old_id:
                changed[k] = v
        elif k == "doctor_id" and hasattr(old, "doctor"):
            old_id = getattr(old.doctor, "id", None) if old.doctor else None
            if v != old_id:
                changed[k] = v
        elif k == "time_range":
            old_val = getattr(old, k, None)
            # Compare as string if either is WatchTimeRange or str
            old_str = str(old_val) if isinstance(old_val, (WatchTimeRange, str)) else old_val
            new_str = str(v) if isinstance(v, (WatchTimeRange, str)) else v
            if old_str != new_str:
                changed[k] = v
        else:
            old_val = getattr(old, k, None)
            if v != old_val:
                changed[k] = v
    return changed


def get_handler_for_state(router: Any, state) -> Any:
    """
    Find a message handler for a specific state in a router or its sub-routers.

    Args:
        router: The router to search in
        state: The state to find a handler for

    Returns:
        The handler callback function

    Raises:
        RuntimeError: If no handler is found for the given state
    """
    # Search handlers in this router
    for handler in getattr(router.message, "handlers", []):
        if hasattr(handler, "filters"):
            for f in handler.filters:
                if hasattr(f, "callback") and hasattr(f.callback, "state") and f.callback.state == state:
                    return handler.callback
    # Recursively search included routers
    for sub_router in getattr(router, "sub_routers", []):
        try:
            return get_handler_for_state(sub_router, state)
        except RuntimeError:
            continue
    raise RuntimeError(f"No handler found for state {state}")


def get_handler_for_state_from_dp(dp: Any, state) -> Any:
    """
    Find a message handler for a specific state in a dispatcher.

    Args:
        dp: The dispatcher to search in
        state: The state to find a handler for

    Returns:
        The handler callback function

    Raises:
        RuntimeError: If no handler is found for the given state
    """
    # Recursively search all routers included in dp
    for router in getattr(dp, "sub_routers", []):
        try:
            return get_handler_for_state(router, state)
        except RuntimeError:
            continue
    raise RuntimeError(f"No handler found for state {state} in dp")


def test_get_watch_by_id_found():
    """Test finding a watch by ID when it exists in the collection."""
    # Arrange
    watches = [DummyWatch(1), DummyWatch(2)]

    # Act
    watch = get_watch_by_id(watches, "2")

    # Assert
    assert watch is not None
    assert watch.id == 2


def test_get_watch_by_id_not_found():
    """Test finding a watch by ID when it doesn't exist in the collection."""
    # Arrange
    watches = [DummyWatch(1), DummyWatch(2)]

    # Act & Assert
    assert get_watch_by_id(watches, "3") is None


def test_get_changed_fields_basic():
    """Test that changed fields are correctly identified in basic cases."""
    # Arrange
    old = DummyWatch(
        1, city="A", clinic=DummyIdValue(10), start_date=datetime.date.fromisoformat("2024-01-01"), auto_book=False
    )
    new = {"city": "B", "clinic_id": 11, "start_date": datetime.date.fromisoformat("2024-01-01"), "auto_book": True}

    # Act
    changed = get_changed_fields(old, new)

    # Assert
    assert changed["city"] == "B"
    assert changed["clinic_id"] == 11
    assert changed["auto_book"] is True
    assert "start_date" not in changed  # unchanged


def test_get_changed_fields_none_values():
    """Test that None values in the new data are ignored and not marked as changes."""
    # Arrange
    old = DummyWatch(1, city="A", clinic=DummyIdValue(10))
    new = {"city": None, "clinic_id": None}

    # Act
    changed = get_changed_fields(old, new)

    # Assert
    assert changed == {}


def test_escape_markdown_all_chars():
    """Test that all special Markdown characters are properly escaped."""
    # Arrange
    text = r"_[]()~`>#+-=|{}.!\test"

    # Act
    escaped = escape_markdown(text)

    # Assert
    for c in "_[]()~`>#+-=|{}.!\\":
        assert f"\\{c}" in escaped


@pytest.mark.asyncio
async def test_edit_watch_full_flow():
    """Test the full edit watch flow with changes that are successfully applied."""
    # Arrange - Setup mocks
    dp = MagicMock()
    dp.sub_routers = []
    watch_service = MagicMock()
    watch_service.get_all_watches = AsyncMock(
        return_value=[DummyWatch(1, city="A", clinic=DummyIdValue(10), auto_book=False)]
    )
    watch_service.list_available_filters = AsyncMock(return_value=[{"id": 10, "value": "ClinicA"}])
    watch_service.update_watch = MagicMock()

    # Register handler and get the auto_book state handler
    router = register_edit_watch_handler(dp, watch_service)
    if router not in dp.sub_routers:
        dp.sub_routers.append(router)
    edit_auto_book = get_handler_for_state_from_dp(dp, EditWatchStates.editing_auto_book)

    # Set up state and message
    state = AsyncMock()
    state.get_data = AsyncMock(
        return_value={
            "watch": DummyWatch(1, city="A", clinic=DummyIdValue(10), auto_book=False),
            "city": "B",
            "clinic": 11,
            "start_date": "2024-01-01",
            "end_date": "2024-01-02",
            "time_range": "09:00:00-10:00:00",
            "exclude": "doctor:123",
            "auto_book": True,
        }
    )
    state.clear = AsyncMock()
    message = AsyncMock()
    message.text = "yes"

    # Act
    await edit_auto_book(message, state)

    # Assert
    watch_service.update_watch.assert_called_once()
    assert "✅ Watch no. 1 updated successfully" in message.answer.call_args.args[0]
    state.clear.assert_awaited_once()


@pytest.mark.asyncio
async def test_edit_watch_no_changes():
    """Test the edit watch flow when no changes are provided."""
    # Arrange - Setup mocks
    dp = MagicMock()
    watch_service = MagicMock()
    watch_service.get_all_watches = AsyncMock(
        return_value=[DummyWatch(1, city="A", clinic=DummyIdValue(10), auto_book=False)]
    )
    watch_service.list_available_filters = AsyncMock(return_value=[{"id": 10, "value": "ClinicA"}])
    watch_service.update_watch = MagicMock()

    # Register handler and get the auto_book state handler
    router = register_edit_watch_handler(dp, watch_service)
    edit_auto_book = get_handler_for_state(router, EditWatchStates.editing_auto_book)

    # Set up state and message with no changes
    state = AsyncMock()
    state.get_data = AsyncMock(
        return_value={
            "watch": DummyWatch(1, city="A", clinic=DummyIdValue(10), auto_book=False),
            "city": "A",
            "clinic": 10,
            "start_date": None,
            "end_date": None,
            "time_range": None,
            "exclude": None,
            "auto_book": False,
        }
    )
    state.clear = AsyncMock()
    message = AsyncMock()
    message.text = "skip"

    # Act
    await edit_auto_book(message, state)

    # Assert
    found = any(
        "⚠️ No changes provided and nothing was updated" in call.args[0] for call in message.answer.await_args_list
    )
    assert found
    state.clear.assert_awaited_once()


@pytest.mark.asyncio
async def test_edit_watch_exception():
    """Test the edit watch flow when an exception occurs during the update."""
    # Arrange - Setup mocks
    dp = MagicMock()
    watch_service = MagicMock()
    watch_service.get_all_watches = AsyncMock(
        return_value=[DummyWatch(1, city="A", clinic=DummyIdValue(10), auto_book=False)]
    )
    watch_service.list_available_filters = AsyncMock(return_value=[{"id": 10, "value": "ClinicA"}])
    watch_service.update_watch = MagicMock(side_effect=Exception("fail"))
    # Register handler and get the auto_book state handler
    router = register_edit_watch_handler(dp, watch_service)
    edit_auto_book = get_handler_for_state(router, EditWatchStates.editing_auto_book)

    # Set up state and message
    state = AsyncMock()
    state.get_data = AsyncMock(
        return_value={
            "watch": DummyWatch(1, city="A", clinic=DummyIdValue(10), auto_book=False),
            "city": "B",
            "clinic": 11,
            "start_date": "2024-01-01",
            "end_date": "2024-01-02",
            "time_range": "09:00:00-10:00:00",
            "exclude": "doctor:123",
            "auto_book": True,
        }
    )
    state.clear = AsyncMock()
    message = AsyncMock()
    message.text = "yes"

    # Act
    await edit_auto_book(message, state)

    # Assert
    found = any("❌ Error updating watch" in call.args[0] for call in message.answer.await_args_list)
    assert found
    state.clear.assert_awaited_once()
