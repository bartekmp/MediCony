"""
Telegram bot command to trigger immediate search cycle (skip waiting period).
Does nothing if there are no watch or medicine searches.
"""

import asyncio
from typing import Optional

from aiogram import Dispatcher, Router, types
from aiogram.filters import Command
from pharmaradar import MedicineWatchdog

from src.logger import log
from src.medicover.services.watch_service import WatchService


def register_search_now_handler(
    dispatcher: Dispatcher,
    wake_event: Optional[asyncio.Event] = None,
    watch_service: Optional[WatchService] = None,
    medicine_service: Optional[MedicineWatchdog] = None,
):
    router = Router()
    command_name = "/search_now"

    @router.message(Command("search_now"))
    async def handle_search_now(message: types.Message):
        log.info(f"↪ Received command: {command_name}")

        # Check if there is anything to search
        watches_count = 0
        medicines_count = 0

        try:
            if watch_service is not None:
                watches = await watch_service.get_all_watches()
                watches_count = len(watches)
        except Exception as e:
            log.error(f"Failed fetching watches in search_now: {e}")

        try:
            if medicine_service is not None:
                medicines = medicine_service.get_all_medicines()
                medicines_count = len(medicines)
        except Exception as e:
            log.error(f"Failed fetching medicines in search_now: {e}")

        if watches_count == 0 and medicines_count == 0:
            await message.answer(
                "📝 Nothing to search. No watches or medicines are configured.\nUse /watch_add or /medicine_add to add some.")
            log.info(f"↩ Finished command: {command_name} (no watches or medicines configured)")
            return

        if wake_event is None:
            await message.answer("ℹ️ Immediate search is not enabled in this mode.")
            log.info(f"↩ Finished command: {command_name} (wake_event not configured)")
            return

        # Signal the daemon to skip sleep and run next cycle immediately
        try:
            await message.answer(
                f"⏩ Triggering immediate search cycle. Watches: {watches_count}, medicines: {medicines_count}.")
            if message.from_user:
                log.info(f"User {message.from_user.id} requested immediate search")
            wake_event.set()
            log.info(f"↩ Finished command: {command_name} (wake requested)")
        except Exception as e:
            log.error(f"Failed to trigger immediate search: {e}")
            await message.answer("❌ Failed to trigger immediate search. Please try again.")

    dispatcher.include_router(router)
