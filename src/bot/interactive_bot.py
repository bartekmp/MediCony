import asyncio
import os
from typing import Optional

from aiogram import Bot, Dispatcher
from pharmaradar import MedicineWatchdog

from src.bot.commands.logs import register_logs_handler
from src.bot.commands.search_now import register_search_now_handler
from src.bot.commands.medicine_activate import register_activate_medicine_handler
from src.bot.commands.medicine_add import register_add_medicine_handler
from src.bot.commands.medicine_edit import register_edit_medicine_handler
from src.bot.commands.medicine_list import register_medicines_handler
from src.bot.commands.medicine_remove import register_remove_medicine_handler
from src.bot.commands.watch_add import register_add_watch_handler
from src.bot.commands.watch_edit import register_edit_watch_handler
from src.bot.commands.watch_list import register_watches_handler
from src.bot.commands.watch_remove import register_remove_watch_handler
from src.bot.telegram import check_env_vars
from src.medicover.services.watch_service import WatchService


class TelegramBot:
    bot: Bot
    dp: Dispatcher

    def __init__(
        self,
        watch_service: Optional[WatchService] = None,
        medicine_service: Optional[MedicineWatchdog] = None,
        wake_event: Optional[asyncio.Event] = None,
    ):
        check_env_vars()
        self.bot = Bot(
            token=os.getenv("MEDICONY_TELEGRAM_TOKEN", ""),
        )
        self.dp = Dispatcher()
        self.watch_service = watch_service
        self.medicine_service = medicine_service
        self.wake_event = wake_event
        self.register_handlers()

    def register_handlers(self):
        # Watch handlers (only if watch_service is provided)
        if self.watch_service:
            register_edit_watch_handler(self.dp, self.watch_service)
            register_watches_handler(self.dp, self.watch_service)
            register_add_watch_handler(self.dp, self.watch_service)
            register_remove_watch_handler(self.dp, self.watch_service)
        register_logs_handler(self.dp)
        # Register search_now handler to trigger immediate search cycles
        register_search_now_handler(self.dp, self.wake_event, self.watch_service, self.medicine_service)

        # Medicine handlers (only if medicine_service is provided)
        if self.medicine_service:
            register_add_medicine_handler(self.dp, self.medicine_service)
            register_medicines_handler(self.dp, self.medicine_service)
            register_remove_medicine_handler(self.dp, self.medicine_service)
            register_edit_medicine_handler(self.dp, self.medicine_service)
            register_activate_medicine_handler(self.dp, self.medicine_service)

    async def dispatch_interactive_bot(self, shutdown_event: asyncio.Event):
        """Start the Telegram bot with graceful shutdown support."""
        try:
            # Start polling in a task so we can check for shutdown
            polling_task = asyncio.create_task(self.dp.start_polling(self.bot))

            # Wait for either polling to finish or shutdown signal
            while not shutdown_event.is_set() and not polling_task.done():
                await asyncio.sleep(0.1)

            # If shutdown was requested, stop polling gracefully
            if shutdown_event.is_set():
                polling_task.cancel()
                try:
                    await polling_task
                except asyncio.CancelledError:
                    pass

        except Exception as e:
            print(f"Error in Telegram bot: {e}")
        finally:
            # Close the bot session
            await self.bot.session.close()
