import os

import numpy as np
from notifiers import get_notifier
from notifiers.exceptions import BadArguments

from src.logger import log
from src.medicover.appointment import Appointment
from src.medicover.watch import Watch

ENV_PREFIX = "MEDICONY_"
MEDICONY_TELEGRAM_CHAT_ID_ENV_VAR = f"{ENV_PREFIX}TELEGRAM_CHAT_ID"
MEDICONY_TELEGRAM_TOKEN_ENV_VAR = f"{ENV_PREFIX}TELEGRAM_TOKEN"
MAX_MESSAGE_LENGTH = 4096

telegram = get_notifier("telegram")


def check_env_vars():
    if (os.getenv(MEDICONY_TELEGRAM_CHAT_ID_ENV_VAR) is None or os.getenv(MEDICONY_TELEGRAM_TOKEN_ENV_VAR) is None) or (
        os.getenv(MEDICONY_TELEGRAM_CHAT_ID_ENV_VAR) == "" or os.getenv(MEDICONY_TELEGRAM_TOKEN_ENV_VAR) == ""
    ):
        log.error(
            f"Telegram notifications require {MEDICONY_TELEGRAM_CHAT_ID_ENV_VAR} and {MEDICONY_TELEGRAM_TOKEN_ENV_VAR} environments to be exported"
        )
        raise EnvironmentError("Telegram environment variables not found")


def is_message_below_max_length(message: str) -> bool:
    return False if len(message) > MAX_MESSAGE_LENGTH else True


def format_single_text_element(element: Appointment | Watch | str) -> str:
    return str(element) + "\n" + "-" * 50


def format_elements_as_text(elements: list[Appointment] | list[Watch] | list[str]) -> str | None:
    if not len(elements):
        return None

    messages = []
    for d in elements:
        messages.append(format_single_text_element(d))
    return "\n".join(messages)


def format_code_element(code: str) -> str:
    return f"<pre><code>{code}</code></pre>"


def create_message_batches(formatted_message: str, elements: list[Appointment] | list[Watch]) -> list[str]:
    calculate_message_batches_count = lambda message: ((len(message) - 1) // MAX_MESSAGE_LENGTH) + 1
    elements_batches = [
        format_single_text_element(split_elements)
        for split_elements in np.array_split(elements, calculate_message_batches_count(formatted_message))  # type: ignore
    ]
    return elements_batches


def send_message(title: str | None, message: str):
    if title:
        message = f"<b>{title}</b>\n{message}"
    try:
        r = telegram.notify(message=message, parse_mode="html", disable_web_page_preview=True, env_prefix=ENV_PREFIX)
    except BadArguments as e:
        log.error("Failed to send the notification")
        log.error(f"{e}")
        return

    if r.status != "Success":
        log.error("Telegram notification failed")
        log.error(f"{r.errors}")


def notify(elements: list[Appointment] | list[Watch], title: str | None = ""):
    check_env_vars()
    formatted_message = format_elements_as_text(elements)
    if not formatted_message:
        log.info("No elements to notify, skipping Telegram notification")
        return
    if is_message_below_max_length(formatted_message):
        send_message(title, formatted_message)
    else:
        elements_batches = create_message_batches(formatted_message, elements)
        log.info(
            f"Message too long for Telegram notification ({MAX_MESSAGE_LENGTH} characters), splitting into {len(elements_batches)} batches"
        )
        for msg in elements_batches:
            send_message(title, msg)

    log.info("Finished sending notifications via Telegram")
