"""
Telegram-based MFA code provider for MediCony.

Sends a message to the user's Telegram chat asking for the 6-digit 2FA code,
waits for their reply, and returns the code to the authenticator.
"""

import asyncio
import os
import re

from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import ForceReply

from src.logger import log

MFA_TIMEOUT_SECONDS = 300  # 5 minutes


class TelegramMfaProvider:
    """Provides MFA codes by asking the user via Telegram and waiting for their reply."""

    def __init__(self, bot: Bot, dispatcher: Dispatcher):
        self.bot = bot
        self.chat_id = os.getenv("MEDICONY_TELEGRAM_CHAT_ID", "")
        self._pending_future: asyncio.Future[str | None] | None = None
        self._mfa_message_id: int | None = None
        self._router = Router()
        self._register_handler()
        dispatcher.include_router(self._router)

    def _register_handler(self):
        """Register a message handler that listens for replies to the MFA prompt message."""

        @self._router.message()
        async def handle_mfa_reply(message: types.Message):
            # Only process replies to our MFA prompt message
            if (
                self._pending_future is not None
                and not self._pending_future.done()
                and message.reply_to_message
                and message.reply_to_message.message_id == self._mfa_message_id
                and message.text
            ):
                code = message.text.strip()
                if re.match(r"^\d{6}$", code):
                    self._pending_future.set_result(code)
                    await message.reply("✅ Code received, verifying...")
                else:
                    await message.reply("⚠️ Invalid code format. Please reply with exactly 6 digits.")

    async def send_prompt(self, channel: str) -> bool:
        """Send the MFA prompt to the user and prepare to wait for their reply."""
        if not self.chat_id:
            log.error("MEDICONY_TELEGRAM_CHAT_ID is not set, cannot request MFA code")
            return False

        loop = asyncio.get_running_loop()
        self._pending_future = loop.create_future()

        try:
            sent_message = await self.bot.send_message(
                chat_id=self.chat_id,
                text=(
                    "🔐 <b>MFA verification required</b>\n\n"
                    f"A 6-digit verification code was sent to you via <b>{channel}</b>.\n"
                    f"Reply to this message with the code within {MFA_TIMEOUT_SECONDS // 60} minutes."
                ),
                parse_mode="html",
                reply_markup=ForceReply(
                    selective=True,
                    input_field_placeholder="Enter 6-digit code",
                ),
            )
            self._mfa_message_id = sent_message.message_id
            log.debug(f"MFA code request sent via Telegram (message_id={self._mfa_message_id})")
            return True

        except Exception as e:
            log.error(f"Failed to request MFA code via Telegram: {e}")
            self._pending_future = None
            return False

    async def wait_for_reply(self) -> str | None:
        """Wait for the user's reply with the MFA code."""
        if not self._pending_future:
            return None

        try:
            code = await asyncio.wait_for(self._pending_future, timeout=MFA_TIMEOUT_SECONDS)
            return code
        except asyncio.TimeoutError:
            log.error("MFA code request timed out — no reply received within the timeout period")
            await self.bot.send_message(
                chat_id=self.chat_id,
                text="⏰ MFA verification timed out. Authentication failed. The next login attempt will request a new code.",
                parse_mode="html",
            )
            # Clear fields on timeout
            self._pending_future = None
            self._mfa_message_id = None
            return None

    async def send_verification_result(self, success: bool, message: str = ""):
        """Send the result of the MFA verification to the user."""
        if not self.chat_id:
            return

        status_text = "✅ <b>Verification successful</b>" if success else f"❌ <b>Verification failed</b>\n\n{message}"
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=status_text,
                parse_mode="html",
                reply_to_message_id=self._mfa_message_id,
            )
        except Exception as e:
            log.error(f"Failed to send verification result via Telegram: {e}")
        finally:
            self._pending_future = None
            self._mfa_message_id = None

    async def request_code(self, channel: str) -> str | None:
        """
        Send a Telegram message asking for the MFA code and wait for the user's reply.

        Args:
            channel: The MFA channel description (e.g., "Email", "SMS").

        Returns:
            The 6-digit code string, or None if the user didn't reply within the timeout.
        """
        if await self.send_prompt(channel):
            return await self.wait_for_reply()
        return None
