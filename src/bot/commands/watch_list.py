from aiogram import Dispatcher
from aiogram.filters import Command

from src.bot.shared_utils import send_formatted_reply
from src.bot.telegram import (
    create_message_batches,
    format_elements_as_text,
    format_single_text_element,
    is_message_below_max_length,
)
from src.logger import log
from src.medicover.services.watch_service import WatchService
from src.medicover.watch import Watch


def register_watches_handler(dp: Dispatcher, watch_service: WatchService):
    command_name = "/watch_list"

    async def handle_watches(message):
        log.info(f"↪ Received command: {command_name}")
        try:
            watches: list[Watch] = await watch_service.get_all_watches()
            if not watches:
                await send_formatted_reply(
                    command_name, message, format_single_text_element("✅ No active watches"), None
                )
                return
            formatted_message = str(format_elements_as_text(watches))
            if is_message_below_max_length(formatted_message):
                response_title = format_single_text_element("📋 Active watches:")
                await send_formatted_reply(command_name, message, response_title, formatted_message)
                log.info(f"Sent single message for command '{command_name}'")
                for line in formatted_message.splitlines():
                    log.info(line)
            else:
                response_title = format_single_text_element("📋 Active watches (split):")
                await send_formatted_reply(command_name, message, response_title, None)
                chunks = create_message_batches(formatted_message, watches)
                for chunk in chunks:
                    await send_formatted_reply(command_name, message, "", chunk)
                log.info(f"Sent {len(chunks)} message chunks for command '{command_name}'")
                for chunk in chunks:
                    log.info(chunk)
        except Exception as e:
            await message.answer("❌ Error while fetching the watch list.")
            log.error(f"Error in handle_watches: {e}")
        finally:
            log.info(f"↩ Finished command: {command_name}")

    dp.message(Command("watch_list"))(handle_watches)
    return handle_watches
