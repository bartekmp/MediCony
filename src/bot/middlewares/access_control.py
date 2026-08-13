import os
from typing import Any, Awaitable, Callable, Optional

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

from src.bot.telegram import ENV_PREFIX
from src.logger import log

MEDICONY_TELEGRAM_ALLOWED_USER_IDS_ENV_VAR = f"{ENV_PREFIX}TELEGRAM_ALLOWED_USER_IDS"


def get_allowed_user_ids() -> set[int]:
    """Parse the comma-separated allow-list of Telegram user IDs from the environment.

    Returns an empty set when the variable is unset or empty, which the middleware
    treats as "no restriction" (backwards-compatible with existing deployments).
    """
    raw = os.getenv(MEDICONY_TELEGRAM_ALLOWED_USER_IDS_ENV_VAR, "")
    allowed: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            allowed.add(int(part))
        except ValueError:
            log.warning(f"Ignoring invalid Telegram user id in {MEDICONY_TELEGRAM_ALLOWED_USER_IDS_ENV_VAR}: {part!r}")
    return allowed


class AccessControlMiddleware(BaseMiddleware):
    """Drop any update coming from a Telegram user that is not on the allow-list.

    The allow-list is read once at construction time from
    ``MEDICONY_TELEGRAM_ALLOWED_USER_IDS`` (comma-separated). It accepts both
    individual user IDs and group/channel chat IDs (which are negative); an
    update is allowed when either its sender or its chat is on the list. When
    the list is empty the middleware is a no-op and everyone is allowed.
    """

    def __init__(self) -> None:
        self.allowed_ids = get_allowed_user_ids()
        if self.allowed_ids:
            log.info(f"Telegram bot access restricted to user/chat ids: {sorted(self.allowed_ids)}")
        else:
            log.warning(
                f"{MEDICONY_TELEGRAM_ALLOWED_USER_IDS_ENV_VAR} is not set - the bot will respond to any Telegram user"
            )

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # No restriction configured -> let everything through.
        if not self.allowed_ids:
            return await handler(event, data)

        user_id, chat_id = self._extract_ids(event)

        # Allow service updates without a user or chat (e.g. poll answers) to pass;
        # they carry no actionable command.
        if user_id is None and chat_id is None:
            return await handler(event, data)

        # Allow when either the sender or the originating chat is on the list.
        if user_id in self.allowed_ids or chat_id in self.allowed_ids:
            return await handler(event, data)

        await self._deny(event, user_id)
        # Returning without calling the handler stops the update from being processed.
        return None

    @staticmethod
    def _extract_ids(event: TelegramObject) -> tuple[Optional[int], Optional[int]]:
        source: Any = event
        if isinstance(event, Update):
            source = event.message or event.callback_query or event.edited_message or event.my_chat_member

        from_user = getattr(source, "from_user", None)
        user_id = from_user.id if from_user else None

        # A callback query has no chat of its own; fall back to the message it decorates.
        chat = getattr(source, "chat", None)
        if chat is None:
            chat = getattr(getattr(source, "message", None), "chat", None)
        chat_id = chat.id if chat else None

        return user_id, chat_id

    @staticmethod
    async def _deny(event: TelegramObject, user_id: int) -> None:
        log.warning(f"Rejected Telegram update from unauthorized user id: {user_id}")
        message: Optional[Message] = None
        if isinstance(event, Update):
            message = event.message or event.edited_message
            if event.callback_query:
                try:
                    await event.callback_query.answer("You are not authorized to use this bot.", show_alert=True)
                except Exception:  # pragma: no cover - best-effort notification
                    pass
                return
        elif isinstance(event, Message):
            message = event
        elif isinstance(event, CallbackQuery):
            try:
                await event.answer("You are not authorized to use this bot.", show_alert=True)
            except Exception:  # pragma: no cover - best-effort notification
                pass
            return

        if message is not None:
            try:
                await message.answer("⛔ You are not authorized to use this bot.")
            except Exception:  # pragma: no cover - best-effort notification
                pass
