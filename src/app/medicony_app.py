"""
Main application module that orchestrates Medicover and Medicine functionalities.
"""

import asyncio
from argparse import Namespace

from src.app.medicine_app import MedicineApp
from src.app.medicover_app import MedicoverApp
from src.bot.interactive_bot import TelegramBot
from src.config import MediConyConfig
from src.database import MedicoverDbClient, PharmaDbClient
from src.logger import log


class MediCony:
    """
    Main application class that orchestrates Medicover and Medicine functionalities.
    """

    def __init__(self, config: MediConyConfig, args: Namespace):
        self.config = config
        self.args = args

        # Determine command from args
        self.command = self.args.command

        # Lazy initialization for MedicoverApp
        if self.command and ("medicine" not in self.command or "start" in self.command):
            self.medicover_app = MedicoverApp(config, MedicoverDbClient(), args)
        else:
            self.medicover_app = None

        # Lazy initialization for MedicineApp
        if self.command and ("medicine" in self.command or "start" in self.command):
            self.medicine_app = MedicineApp(config, PharmaDbClient(), args)
        else:
            self.medicine_app = None

    async def authenticate(self):
        """Authenticate with Medicover API."""
        if self.medicover_app:
            await self.medicover_app.authenticate()
        else:
            log.info("MedicoverApp not initialized (command contains 'medicine' and is not 'start')")

    # Medicover-related commands
    async def find_appointment(self):
        if self.medicover_app:
            await self.medicover_app.find_appointment()
        else:
            log.info("MedicoverApp not initialized (command contains 'medicine' and is not 'start')")

    async def book_appointment(self):
        if self.medicover_app:
            await self.medicover_app.book_appointment()
        else:
            log.info("MedicoverApp not initialized (command contains 'medicine' and is not 'start')")

    async def list_filters(self):
        if self.medicover_app:
            await self.medicover_app.list_filters()
        else:
            log.info("MedicoverApp not initialized (command contains 'medicine' and is not 'start')")

    def add_watch(self):
        if self.medicover_app:
            self.medicover_app.add_watch()
        else:
            log.info("MedicoverApp not initialized (command contains 'medicine' and is not 'start')")

    async def edit_watch(self):
        if self.medicover_app:
            await self.medicover_app.edit_watch()
        else:
            log.info("MedicoverApp not initialized (command contains 'medicine' and is not 'start')")

    def remove_watch(self):
        if self.medicover_app:
            self.medicover_app.remove_watch()
        else:
            log.info("MedicoverApp not initialized (command contains 'medicine' and is not 'start')")

    async def list_watches(self):
        if self.medicover_app:
            await self.medicover_app.list_watches()
        else:
            log.info("MedicoverApp not initialized (command contains 'medicine' and is not 'start')")

    async def list_appointments(self):
        if self.medicover_app:
            await self.medicover_app.list_appointments()
        else:
            log.info("MedicoverApp not initialized (command contains 'medicine' and is not 'start')")

    async def cancel_appointment(self):
        if self.medicover_app:
            await self.medicover_app.cancel_appointment()
        else:
            log.info("MedicoverApp not initialized (command contains 'medicine' and is not 'start')")

    # Medicine-related commands
    def add_medicine(self):
        if self.medicine_app:
            self.medicine_app.add_medicine()
        else:
            log.info("MedicineApp not initialized (command does not contain 'medicine' or is not 'start')")

    def remove_medicine(self):
        if self.medicine_app:
            self.medicine_app.remove_medicine()
        else:
            log.info("MedicineApp not initialized (command does not contain 'medicine' or is not 'start')")

    def list_medicines(self):
        if self.medicine_app:
            self.medicine_app.list_medicines()
        else:
            log.info("MedicineApp not initialized (command does not contain 'medicine' or is not 'start')")

    def edit_medicine(self):
        if self.medicine_app:
            self.medicine_app.edit_medicine()
        else:
            log.info("MedicineApp not initialized (command does not contain 'medicine' or is not 'start')")

    async def search_medicine(self):
        if self.medicine_app:
            await self.medicine_app.search_medicine()
        else:
            log.info("MedicineApp not initialized (command does not contain 'medicine' or is not 'start')")

    async def daemon_mode(self, sleep_period_s: int, shutdown_event: asyncio.Event, wake_event: asyncio.Event | None = None):
        log.info(f"Daemon mode. Sleep period: {sleep_period_s}s")
        if not self.medicover_app and not self.medicine_app:
            log.info("Neither MedicoverApp nor MedicineApp initialized, exiting daemon mode")
            return

        while not shutdown_event.is_set():
            try:
                if self.medicover_app:
                    log.info("=== Starting Medicover appointment search")
                    await self._search_appointments()

                if self.medicine_app:
                    log.info("=== Starting Medicine search")
                    await self._search_medicines()
            except Exception as e:
                log.error(f"Error in daemon cycle: {str(e)}")

            # Check for shutdown before sleeping
            if shutdown_event.is_set():
                log.info("Shutdown requested, exiting daemon mode")
                break

            log.info(f"=== Sleeping for {sleep_period_s}s")

            # Sleep in smaller intervals to check shutdown event periodically
            sleep_interval = 1  # Check every second
            total_slept = 0

            while total_slept < sleep_period_s and not shutdown_event.is_set():
                try:
                    # If a wake_event is provided and set, break sleep early
                    if wake_event is not None and wake_event.is_set():
                        log.info("Wake event received. Skipping remaining sleep and running next cycle now.")
                        wake_event.clear()
                        break

                    remaining_sleep = min(sleep_interval, sleep_period_s - total_slept)
                    await asyncio.sleep(remaining_sleep)
                    total_slept += remaining_sleep
                except asyncio.CancelledError:
                    log.info("Sleep cancelled, shutting down")
                    break

            # Double-check shutdown event after sleep
            if shutdown_event.is_set():
                log.info("Shutdown requested during sleep, exiting daemon mode")
                break

        log.info("Daemon mode stopped")

    async def _search_appointments(self):
        if self.medicover_app:
            await self.medicover_app.search_appointments()
        else:
            log.info("MedicoverApp not initialized (command contains 'medicine' and is not 'start')")

    async def _search_medicines(self):
        if self.medicine_app:
            await self.medicine_app.search_medicines()
        else:
            log.info("MedicineApp not initialized (command does not contain 'medicine' or is not 'start')")

    # Enhanced version of daemon_worker that uses a singleton TelegramBot
    async def daemon_worker(self, sleep_period_s: int, shutdown_event: asyncio.Event):
        if not self.medicover_app or not self.medicine_app:
            log.info("MedicoverApp and MedicineApp must be both initialized, exiting daemon worker")
            return

        # Wake event to allow external triggers (e.g., Telegram command) to skip sleep
        wake_event = asyncio.Event()

        telegram_bot = TelegramBot(
            self.medicover_app.watch_service,
            self.medicine_app.medicine_service,
            wake_event,
        )

        # Run bot and main loop as cancellable tasks; cancel on shutdown for fast exit
        bot_task = asyncio.create_task(telegram_bot.dispatch_interactive_bot(shutdown_event))
        loop_task = asyncio.create_task(self.daemon_mode(sleep_period_s, shutdown_event, wake_event))

        shutdown_wait = asyncio.create_task(shutdown_event.wait())
        try:
            # Wait until either shutdown is requested or any task finishes
            done, pending = await asyncio.wait(
                {bot_task, loop_task, shutdown_wait}, return_when=asyncio.FIRST_COMPLETED
            )

            # If shutdown requested, cancel running tasks
            if shutdown_wait in done:
                for t in (bot_task, loop_task):
                    if not t.done():
                        t.cancel()
            else:
                # If any of the tasks finished (error or normal), cancel the other and stop
                for t in (bot_task, loop_task):
                    if not t.done():
                        t.cancel()

            # Await cancellations to settle
            for t in (bot_task, loop_task):
                try:
                    await t
                except asyncio.CancelledError:
                    pass
        finally:
            for t in (shutdown_wait,):
                if not t.done():
                    t.cancel()
            log.info("Daemon worker stopped. Cleaning up resources...")
