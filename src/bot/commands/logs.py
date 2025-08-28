from aiogram import Dispatcher, types
from aiogram.filters import Command

from src.bot.shared_utils import send_formatted_reply
from src.bot.telegram import format_code_element
from src.logger import log, read_n_log_lines_from_file


def register_logs_handler(dp: Dispatcher, send_formatted_reply_override=None):
    send_reply = send_formatted_reply_override or send_formatted_reply
    command_name = "/logs"

    async def handle_logs(message: types.Message):
        log.info(f"↪ Received command: {command_name}")
        try:
            log_lines = read_n_log_lines_from_file()
            if not log_lines:
                await send_reply(command_name, message, "❌ No logs found.", None)
                return
            response_title = "📜 Last 30 lines of logs:"
            await send_reply(command_name, message, response_title, format_code_element(log_lines))
            log.info("Reply to command 'logs' sent:")
            log_lines_message = response_title + "\n" + log_lines
            for line in log_lines_message.splitlines():
                log.info(line)
        except Exception as e:
            await message.answer("❌ Error while fetching logs.")
            log.error(f"Error in handle_logs: {e}")
        finally:
            log.info(f"↩ Finished command: {command_name}")

    dp.message(Command("logs"))(handle_logs)
    return handle_logs
