import os
import re

from aiogram import types
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def is_abort(text: str) -> bool:
    return strip_leading_emoji(text.strip().lower()) == "abort"


def is_skip(text: str) -> bool:
    return strip_leading_emoji(text.strip().lower()) == "skip"


def strip_leading_emoji(text: str) -> str:
    return re.sub(r"^\W+\s*", "", text)


def escape_markdown(text: str) -> str:
    text = text.replace("\\", "\\\\")
    chars = "_[]()~`>#+-=|{}.!"
    for c in chars:
        text = text.replace(c, f"\\{c}")
    return text


def format_current_value(label: str, value=None) -> str:
    if value is None:
        return ""
    if type(value).__str__ is object.__str__:
        return f"Current {label}: N/A\n"
    if str(value) == "":
        return f"Current {label}: not set\n"
    escaped_value = escape_markdown(str(value))
    escaped_value = escaped_value.replace("*", "\\*")  # Escape * in value
    return f"Current *{escape_markdown(label)}*: *{escaped_value}*\n"


def id_keyboard(ids: list, add_abort: bool = True, add_skip: bool = False, n_cols: int = 3) -> ReplyKeyboardMarkup:
    if add_skip:
        ids = ["↪️ Skip"] + ids
    if add_abort:
        ids = ["🚫 Abort"] + ids
    rows = [[KeyboardButton(text=str(i)) for i in ids[j : j + n_cols]] for j in range(0, len(ids), n_cols)]
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def two_column_keyboard(items: list[str], add_abort: bool = True, add_skip: bool = False) -> ReplyKeyboardMarkup:
    if add_skip:
        items = ["↪️ Skip"] + items
    if add_abort:
        items = ["🚫 Abort"] + items
    rows = [
        (
            [KeyboardButton(text=items[i]), KeyboardButton(text=items[i + 1])]
            if i + 1 < len(items)
            else [KeyboardButton(text=items[i])]
        )
        for i in range(0, len(items), 2)
    ]
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def abort_keyboard(extra_buttons=None) -> ReplyKeyboardMarkup:
    # extra_buttons: list of strings to add as extra buttons (one per row)
    keyboard = [[KeyboardButton(text="🚫 Abort")]]
    if extra_buttons:
        for btn in extra_buttons:
            keyboard.append([KeyboardButton(text=btn)])
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def abort_and_skip_keyboard(extra_buttons=None) -> ReplyKeyboardMarkup:
    # extra_buttons: list of strings to add as extra buttons (one per row)
    keyboard = [[KeyboardButton(text="🚫 Abort")], [KeyboardButton(text="↪️ Skip")]]
    if extra_buttons:
        for btn in extra_buttons:
            keyboard.append([KeyboardButton(text=btn)])
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def ask_with_skip(
    message: types.Message,
    prompt: str,
    format: str | None = None,
    current_value=None,
    keyboard: ReplyKeyboardMarkup | None = None,
):
    format_text = f"\nFormat: *{escape_markdown(format)}*\n" if format else ""
    text = f"{format_current_value(prompt, current_value)}▶️ Enter new *{prompt}* or press *Skip*:\n{format_text}"
    return message.answer(text, parse_mode="MarkdownV2", reply_markup=keyboard or abort_and_skip_keyboard())


def get_suggested_properties():
    env = os.getenv("TELEGRAM_ADD_COMMAND_SUGGESTED_PROPERTIES", "")
    result = {}
    for part in env.split(";"):
        if not part.strip():
            continue
        if ":" in part:
            k, v = part.split(":", 1)
            # For region, allow value like "200[Region Name]" or just "200"
            if k.strip() == "region":
                m = re.match(r"(\d+)(\[.*\])?", v.strip())
                if m:
                    result[k.strip()] = {"value": m.group(1), "label": v.strip()}
                else:
                    result[k.strip()] = {"value": v.strip(), "label": v.strip()}
            else:
                result[k.strip()] = v.strip()
    return result


async def send_formatted_reply(command: str, event: types.Message, title: str, message: str | None = None):
    message_to_send = ""
    if title:
        message_to_send += f"<b>{title}</b>"
        if message:
            message_to_send += f"\n{message}"
    try:
        await event.answer(
            text=message_to_send,
            parse_mode="html",
        )
    except Exception as e:
        await event.answer(
            text=f"❌ Error while processing command '{command}': {e}",
            parse_mode="html",
        )
    return
