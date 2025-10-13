#!/usr/bin/python3

import asyncio
import signal
import sys

from dotenv import load_dotenv

from src.app.medicony_app import MediCony
from src.config import get_config
from src.logger import log
from src.parse_args import command_line_parser

# Load environment variables
load_dotenv()

def _make_signal_handler(shutdown_event: asyncio.Event):
    """Create a signal handler that sets the provided shutdown event."""
    def _handler(signum, frame):
        log.info(f"Received signal {signum}. Initiating graceful shutdown...")
        shutdown_event.set()

    return _handler


async def main():
    # Create shutdown event inside the running loop and set up signal handlers
    shutdown_event = asyncio.Event()
    handler = _make_signal_handler(shutdown_event)
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)

    args = command_line_parser().parse_args()
    # Get centralized configuration
    config = get_config()

    # Update logger with config path
    log.set_log_path(config.log_path)

    # Keep the file logging only for the daemon mode, other modes log to console only
    if args.command != "start":
        log.setup_console_only()

    log.info("Properties:")
    for key, value in config.get_env_info().items():
        log.info(f"{key} = {value}")
    log.info("")
    log.info(f"Command line arguments: {args.command}")
    log.info("")

    medicony = MediCony(config, args)
    await medicony.authenticate()

    match args.command:
        case "find-appointment":
            await medicony.find_appointment()
        case "book-appointment":
            await medicony.book_appointment()
        case "list-filters":
            await medicony.list_filters()
        case "add-watch":
            medicony.add_watch()
        case "edit-watch":
            await medicony.edit_watch()
        case "remove-watch":
            medicony.remove_watch()
        case "list-watches":
            await medicony.list_watches()
        case "list-appointments":
            await medicony.list_appointments()
        case "cancel-appointment":
            await medicony.cancel_appointment()
        case "list-accounts":
            aliases = config.list_account_aliases()
            log.info("Configured Medicover accounts:")
            for a in aliases:
                marker = " (default)" if a == config.medicover_default_account else ""
                log.info(f" - {a}{marker}")
        case "add-medicine":
            medicony.add_medicine()
        case "remove-medicine":
            medicony.remove_medicine()
        case "list-medicines":
            medicony.list_medicines()
        case "edit-medicine":
            medicony.edit_medicine()
        case "search-medicine":
            await medicony.search_medicine()
        case "start":
            # Use daemon_worker for starting the daemon with Telegram bot
            await medicony.daemon_worker(config.sleep_period_seconds, shutdown_event)
        case _:
            log.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    log.info("⮦ Started MediCony")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Received KeyboardInterrupt, shutting down...")
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        log.info("↳ Finished MediCony")
