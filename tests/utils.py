"""
Utility functions and classes for MediCony tests.
"""

import random
from typing import Any, Callable, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock

from aiogram import Dispatcher, Router
from aiogram.fsm.context import FSMContext

from src.medicover.appointment import Appointment
from src.id_value_util import IdValue


def generate_random_appointment() -> Appointment:
    """Generate a random appointment for testing."""
    clinic_id = random.randint(1, 1000)
    clinic_name = f"Clinic {clinic_id}"
    doctor_id = random.randint(1, 1000)
    doctor_name = f"Doctor {doctor_id}"
    specialty_id = random.randint(1, 1000)
    specialty_name = f"Specialty {specialty_id}"
    date_time = f"{random.randint(2023, 2025)}-{str(random.randint(1, 12)).zfill(2)}-{str(random.randint(1, 28)).zfill(2)} {str(random.randint(0, 23)).zfill(2)}:{str(random.randint(0, 59)).zfill(2)}:00"
    visit_type = random.choice(["Center", "Examination"])
    booking_string = f"BookingString {random.randint(1, 1000)}"
    booking_identifier = random.randint(1, 1000)
    return Appointment.initialize(
        IdValue(clinic_id, clinic_name),
        date_time,
        IdValue(doctor_id, doctor_name),
        IdValue(specialty_id, specialty_name),
        visit_type,
        booking_string,
        booking_identifier,
    )


def generate_random_appointments(n: int = random.randint(1, 15)) -> List[Appointment]:
    """Generate a list of random appointments for testing."""
    appointments = []
    for _ in range(n):
        appointments.append(generate_random_appointment())
    return appointments


class DummyMessage:
    """Mock implementation of a Telegram message for testing purposes."""

    def __init__(self, text: Optional[str] = None):
        self.text = text
        self.answered: List[Tuple[str, Dict[str, Any]]] = []

    async def answer(self, text: str, **kwargs: Any) -> str:
        """Simulate responding to a message."""
        self.answered.append((text, kwargs))
        return text


def create_mock_fsm_context(initial_data: Optional[Dict[str, Any]] = None) -> MagicMock:
    """Create a mock FSMContext for testing state machine handlers."""
    state = MagicMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value=initial_data or {})
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    return state


def setup_command_handler(
    handler_register_func: Callable, watch_service: Optional[MagicMock] = None, **kwargs: Any
) -> Tuple[MagicMock, Router]:
    """Set up a command handler with dispatcher and router for testing."""
    dp = MagicMock(spec=Dispatcher)
    dp.sub_routers = []

    if watch_service is None:
        watch_service = MagicMock()

    router = handler_register_func(dp, watch_service, **kwargs)

    if hasattr(router, "sub_routers") and router not in dp.sub_routers:
        dp.sub_routers.append(router)

    return dp, router


def setup_watch_service(
    available_filters: Optional[List[Dict[str, Any]]] = None, watches: Optional[List[Any]] = None
) -> MagicMock:
    """Create a mock watch service for testing."""
    watch_service = MagicMock()

    if available_filters is not None:
        watch_service.list_available_filters = AsyncMock(return_value=available_filters)
    else:
        watch_service.list_available_filters = AsyncMock(
            side_effect=lambda what, **kwargs: [{"id": 1, "value": "A"}, {"id": 2, "value": "B"}]
        )

    if watches is not None:
        watch_service.get_all_watches = AsyncMock(return_value=watches)

    watch_service.add_watch = MagicMock()
    watch_service.remove_watch = MagicMock()

    return watch_service


async def process_conversation(
    router: Router, handlers_path: List[int], messages: List[str], state: MagicMock
) -> List[DummyMessage]:
    """Process a conversation through multiple handlers."""
    responses = []
    for i, message_text in enumerate(messages):
        msg = DummyMessage(message_text)
        await router.message.handlers[handlers_path[i]].callback(msg, state)
        responses.append(msg)
    return responses
