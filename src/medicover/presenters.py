from src.logger import log

from .appointment import Appointment
from .watch import Watch


def format_entity_by_lines(entities: list[Watch] | list[Appointment]) -> list[str]:
    messages: list[str] = []
    for e in entities:
        messages.append(str(e))
    return messages


def format_message_chunks(messages: list[str]) -> list[str]:
    formatted_messages: list[str] = []
    for m in messages:
        formatted_messages.append("-" * 50)
        for line in m.splitlines():
            formatted_messages.append(line)
    formatted_messages.append("-" * 50)
    return formatted_messages


def log_entities_with_info(appointments: list[Appointment] | None):
    if not appointments:
        return
    else:
        log.info("Items found:")
        for line in format_message_chunks(format_entity_by_lines(appointments)):
            log.info(line)


def log_entities(entities: list[Appointment] | list[Watch]):
    for line in format_message_chunks(format_entity_by_lines(entities)):
        log.info(line)
