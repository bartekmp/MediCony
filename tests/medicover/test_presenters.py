"""
Tests for the presenters module functionality.

This module tests the functions in the presenters module that handle
formatting and displaying of appointments, watches, and other entities
for various outputs including console, log, and user interfaces.
"""

from typing import List

from src.medicover.presenters import format_entity_by_lines, format_message_chunks, log_entities_with_info
from tests.utils import generate_random_appointment, generate_random_appointments


def test_format_single_appointment() -> None:
    """
    Test formatting a single appointment into a human-readable string.

    Verifies that format_entity_by_lines correctly formats a single appointment
    with all its fields into a readable multi-line string.
    """
    # Arrange
    ap = generate_random_appointment()
    expected_format = [
        f"Date: {ap.date_time}\nClinic: {ap.clinic.value}\nDoctor: {ap.doctor.value}\nSpecialty: {ap.specialty.value}\nType: {ap.visit_type}\nBooked: Yes (ID: {ap.booking_identifier})\nAccount: N/A"
    ]

    # Act
    formatted = format_entity_by_lines([ap])

    # Assert
    assert formatted == expected_format, "Single appointment should be formatted correctly"


def test_format_many_appointments() -> None:
    """
    Test formatting multiple appointments into human-readable strings.

    Verifies that format_entity_by_lines correctly formats a list of appointments
    with all their fields into readable multi-line strings.
    """
    # Arrange
    aps = generate_random_appointments(10)
    expected_format: List[str] = []
    for ap in aps:
        expected_format.append(
            f"Date: {ap.date_time}\nClinic: {ap.clinic.value}\nDoctor: {ap.doctor.value}\nSpecialty: {ap.specialty.value}\nType: {ap.visit_type}\nBooked: Yes (ID: {ap.booking_identifier})\nAccount: N/A"
        )

    # Act
    formatted = format_entity_by_lines(aps)

    # Assert
    assert formatted == expected_format, "Multiple appointments should be formatted correctly"


def test_format_message_chunks() -> None:
    """
    Test formatting message chunks with separators.

    Verifies that format_message_chunks correctly formats a list of multi-line
    messages into a flattened list with separators between each message.
    """
    # Arrange
    messages = ["Hello\nWorld", "This\nis\na\ntest"]
    expected = [
        "-" * 50,
        "Hello",
        "World",
        "-" * 50,
        "This",
        "is",
        "a",
        "test",
        "-" * 50,
    ]

    # Act
    formatted = format_message_chunks(messages)

    # Assert
    assert formatted == expected, "Message chunks should be formatted with separators"


def test_log_appointments(mocker) -> None:
    """
    Test logging of appointments.

    Verifies that log_entities_with_info correctly logs appointment information
    with appropriate formatting and separators.

    Args:
        mocker: The pytest-mock fixture.
    """
    # Arrange
    mock_log = mocker.patch("src.medicover.presenters.log")
    appointments = generate_random_appointments(5)

    # Act
    log_entities_with_info(appointments)

    # Assert
    expected_call_count = (len(str(appointments[0]).splitlines()) + 1) * len(appointments) + 2
    assert mock_log.info.call_count == expected_call_count, "Should log the correct number of lines"

    # Verify first lines are header and separator
    assert mock_log.info.call_args_list[0][0][0] == "Items found:", "First log should be a header"
    assert mock_log.info.call_args_list[1][0][0] == "-" * 50, "Second log should be a separator"

    # Verify appointment details are logged correctly
    i = 2  # Skip header and first separator
    for ap in appointments:
        # Get the logged lines for the current appointment (7 lines per appointment now)
        all_log_params = [val[0][0] for val in mock_log.info.call_args_list[i : i + 7]]
        expected_lines = f"Date: {ap.date_time}\nClinic: {ap.clinic.value}\nDoctor: {ap.doctor.value}\nSpecialty: {ap.specialty.value}\nType: {ap.visit_type}\nBooked: Yes (ID: {ap.booking_identifier})\nAccount: N/A".splitlines()

        assert all_log_params == expected_lines, f"Appointment {i // 8} should be logged correctly"
        i += 8  # 7 lines + 1 separator between appointments
