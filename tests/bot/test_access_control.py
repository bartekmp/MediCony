"""Tests for the Telegram access-control middleware."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import CallbackQuery, Update

from src.bot.middlewares.access_control import (
    MEDICONY_TELEGRAM_ALLOWED_USER_IDS_ENV_VAR,
    AccessControlMiddleware,
    get_allowed_user_ids,
)

USERS = "111111111,222222222"
GROUP_ID = -1001234567890
WITH_GROUP = f"{USERS},{GROUP_ID}"


def _make_update(user_id=None, chat_id=None, *, callback=False):
    """Build a MagicMock that passes isinstance(event, Update) with a single sub-event."""
    update = MagicMock(spec=Update)
    update.message = None
    update.edited_message = None
    update.callback_query = None
    update.my_chat_member = None

    if user_id is None and chat_id is None:
        return update

    from_user = MagicMock(id=user_id) if user_id is not None else None
    chat = MagicMock(id=chat_id) if chat_id is not None else None

    if callback:
        cq = MagicMock(spec=CallbackQuery)
        cq.from_user = from_user
        cq.answer = AsyncMock()
        cq.message = MagicMock(chat=chat) if chat is not None else None
        update.callback_query = cq
    else:
        msg = MagicMock()
        msg.from_user = from_user
        msg.chat = chat
        msg.answer = AsyncMock()
        update.message = msg
    return update


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("111111111,222222222", {111111111, 222222222}),
        (" 111111111 , 222222222 ", {111111111, 222222222}),
        ("111111111,bad,222222222", {111111111, 222222222}),
        ("111111111,111111111", {111111111}),
        ("111111111,-1001234567890", {111111111, -1001234567890}),
        ("", set()),
        ("   ", set()),
    ],
)
def test_get_allowed_user_ids_parsing(raw, expected):
    with patch.dict("os.environ", {MEDICONY_TELEGRAM_ALLOWED_USER_IDS_ENV_VAR: raw}):
        assert get_allowed_user_ids() == expected


def _middleware(allow_value):
    with patch.dict("os.environ", {MEDICONY_TELEGRAM_ALLOWED_USER_IDS_ENV_VAR: allow_value}):
        return AccessControlMiddleware()


@pytest.mark.asyncio
async def test_no_restriction_allows_any_user():
    middleware = _middleware("")
    handler = AsyncMock(return_value="OK")
    update = _make_update(999999)

    result = await middleware(handler, update, {})

    assert result == "OK"
    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_allowed_user_passes_through():
    middleware = _middleware(USERS)
    handler = AsyncMock(return_value="OK")
    update = _make_update(111111111)

    result = await middleware(handler, update, {})

    assert result == "OK"
    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_disallowed_user_is_blocked():
    middleware = _middleware(USERS)
    handler = AsyncMock(return_value="OK")
    update = _make_update(424242)

    result = await middleware(handler, update, {})

    assert result is None
    handler.assert_not_awaited()
    update.message.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_allowed_group_chat_passes_even_for_unlisted_user():
    """Any member of an allow-listed group chat may command the bot."""
    middleware = _middleware(WITH_GROUP)
    handler = AsyncMock(return_value="OK")
    # Sender is not on the list, but the group chat is.
    update = _make_update(user_id=888888, chat_id=GROUP_ID)

    result = await middleware(handler, update, {})

    assert result == "OK"
    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_unlisted_group_chat_is_blocked():
    middleware = _middleware(WITH_GROUP)
    handler = AsyncMock(return_value="OK")
    update = _make_update(user_id=888888, chat_id=-1009999999999)

    result = await middleware(handler, update, {})

    assert result is None
    handler.assert_not_awaited()
    update.message.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_disallowed_callback_query_gets_alert():
    middleware = _middleware(USERS)
    handler = AsyncMock(return_value="OK")
    update = _make_update(424242, callback=True)

    result = await middleware(handler, update, {})

    assert result is None
    handler.assert_not_awaited()
    update.callback_query.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_without_user_passes_through():
    """Service updates that carry no user or chat must not be dropped."""
    middleware = _middleware(USERS)
    handler = AsyncMock(return_value="OK")
    update = _make_update(None)

    result = await middleware(handler, update, {})

    assert result == "OK"
    handler.assert_awaited_once()
