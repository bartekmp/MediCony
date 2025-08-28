"""
Tests for the Appointment class functionality.

This module tests the initialization, comparison, string representation, and
other methods of the Appointment class, which represents medical appointments
in the MediCony application.
"""

from datetime import datetime
from typing import Any, Dict

from src.id_value_util import IdValue
from src.medicover.appointment import Appointment


def test_appointment_init() -> None:
    """
    Test initialization of an Appointment from a standard data dictionary.

    Verifies that the Appointment constructor correctly extracts and converts
    data from a dictionary with standard appointment fields.
    """
    # Arrange
    data: Dict[str, Any] = {
        "appointmentDate": "2025-03-03 12:00:00",
        "clinic": {"id": "123", "name": "clinic123"},
        "doctor": {"id": "567", "name": "doctor567"},
        "specialty": {"id": "890", "name": "specialty890"},
        "visitType": "Center",
    }

    # Act
    ap = Appointment(data)

    # Assert
    assert ap.date_time == datetime.fromisoformat("2025-03-03 12:00:00"), "Date should be correctly parsed"
    assert ap.clinic == IdValue(123, "clinic123"), "Clinic should be correctly extracted as IdValue"
    assert ap.doctor == IdValue(567, "doctor567"), "Doctor should be correctly extracted as IdValue"
    assert ap.specialty == IdValue(890, "specialty890"), "Specialty should be correctly extracted as IdValue"
    assert ap.visit_type == "Center", "Visit type should be correctly extracted"
    assert ap.booking_string is None, "Booking string should be None when not provided"
    assert ap.booking_identifier is None, "Booking identifier should be None when not provided"


def test_appointment_init_alternative_date() -> None:
    """
    Test initialization of an Appointment with alternative date field.

    Verifies that the Appointment constructor correctly handles data dictionaries
    that use 'date' instead of 'appointmentDate' for the appointment date.
    """
    # Arrange
    data: Dict[str, Any] = {
        "date": "2025-03-03 12:00:00",
        "clinic": {"id": "123", "name": "clinic123"},
        "doctor": {"id": "567", "name": "doctor567"},
        "specialty": {"id": "890", "name": "specialty890"},
        "visitType": "Center",
    }

    # Act
    ap = Appointment(data)

    # Assert
    assert ap.date_time == datetime.fromisoformat(
        "2025-03-03 12:00:00"
    ), "Date should be correctly parsed from 'date' field"
    assert ap.clinic == IdValue(123, "clinic123"), "Clinic should be correctly extracted as IdValue"
    assert ap.doctor == IdValue(567, "doctor567"), "Doctor should be correctly extracted as IdValue"
    assert ap.specialty == IdValue(890, "specialty890"), "Specialty should be correctly extracted as IdValue"
    assert ap.visit_type == "Center", "Visit type should be correctly extracted"
    assert ap.booking_string is None, "Booking string should be None when not provided"
    assert ap.booking_identifier is None, "Booking identifier should be None when not provided"


def test_appointment_full_init():
    data = {
        "appointmentDate": "2020-01-01 10:00:00",
        "clinic": {"id": "111", "name": "clinic111"},
        "doctor": {"id": "222", "name": "doctor222"},
        "specialty": {"id": "333", "name": "specialty333"},
        "visitType": "xde",
        "bookingString": "qwertyuiop000",
    }
    ap = Appointment(data)

    assert ap.date_time == datetime.fromisoformat("2020-01-01 10:00:00")
    assert ap.clinic == IdValue(111, "clinic111")
    assert ap.doctor == IdValue(222, "doctor222")
    assert ap.specialty == IdValue(333, "specialty333")
    assert ap.visit_type == "xde"
    assert ap.booking_string == "qwertyuiop000"
    assert ap.booking_identifier is None


def test_appointment_no_data_init():
    ap = Appointment()
    assert not hasattr(ap, "clinic")
    assert not hasattr(ap, "date_time")
    assert not hasattr(ap, "doctor")
    assert not hasattr(ap, "specialty")
    assert ap.visit_type == "Center"
    assert ap.booking_string is None
    assert ap.booking_identifier is None


def test_appointment_initializer_method():
    clinic = IdValue(333, "clinic333")
    doctor = IdValue(555, "doctor555")
    specialty = IdValue(888, "specialty888")
    date_time = "2030-01-25 11:15:00"
    visit_type = "abcdef"

    ap = Appointment.initialize(clinic, date_time, doctor, specialty, visit_type)

    assert ap.date_time == datetime.fromisoformat(date_time)
    assert ap.clinic == clinic
    assert ap.doctor == doctor
    assert ap.specialty == specialty
    assert ap.visit_type == visit_type
    assert ap.booking_identifier is None
    assert ap.booking_string is None


def test_appointment_full_initializer_method():
    clinic = IdValue(333, "clinic333")
    doctor = IdValue(555, "doctor555")
    specialty = IdValue(888, "specialty888")
    date_time = "2030-01-25 11:15:00"
    visit_type = "abcdef"
    booking_string = "qwe"
    booking_identifier = 12345

    ap = Appointment.initialize(clinic, date_time, doctor, specialty, visit_type, booking_string, booking_identifier)

    assert ap.date_time == datetime.fromisoformat(date_time)
    assert ap.clinic == clinic
    assert ap.doctor == doctor
    assert ap.specialty == specialty
    assert ap.visit_type == visit_type
    assert ap.booking_identifier == booking_identifier
    assert ap.booking_string == booking_string


def test_appointment_tuple_init():
    data = (0, 123, 456, "2020-11-11 09:30:00", 789, "xdd", "aaaa", 1337, None)
    ap = Appointment.initialize_from_tuple(data)

    assert ap.date_time == datetime.fromisoformat("2020-11-11 09:30:00")
    assert ap.clinic == IdValue(123)
    assert ap.doctor == IdValue(456)
    assert ap.specialty == IdValue(789)
    assert ap.visit_type == "xdd"
    assert ap.booking_string == "aaaa"
    assert ap.booking_identifier == 1337


def test_appointment_compare():
    data1 = (0, 123, 456, "2020-11-11 09:30:00", 789, "xdd", "aaaa", 1337, None)
    ap1 = Appointment.initialize_from_tuple(data1)

    data2 = (0, 123, 456, "2020-11-11 09:30:00", 789, "xdd", "aaaa", 1337, None)
    ap2 = Appointment.initialize_from_tuple(data2)

    data3 = (0, 444, 555, "1999-11-11 19:10:00", 111, "cccc", "bbbb", 12323, None)
    ap3 = Appointment.initialize_from_tuple(data3)

    assert ap1 == ap2
    assert ap1 != ap3
    assert ap2 != ap3


def test_appointment_to_str():
    data = {
        "appointmentDate": "2020-01-01 10:00:00",
        "clinic": {"id": "111", "name": "clinic111"},
        "doctor": {"id": "222", "name": "doctor222"},
        "specialty": {"id": "333", "name": "specialty333"},
        "visitType": "xde",
        "bookingString": "qwertyuiop000",
    }
    ap = Appointment(data)
    assert (
        str(ap)
        == "Date: 2020-01-01 10:00:00\nClinic: clinic111\nDoctor: doctor222\nSpecialty: specialty333\nType: xde\nBooked: No\nAccount: N/A"
    )

    ap.booking_identifier = 123
    assert (
        str(ap)
        == "Date: 2020-01-01 10:00:00\nClinic: clinic111\nDoctor: doctor222\nSpecialty: specialty333\nType: xde\nBooked: Yes (ID: 123)\nAccount: N/A"
    )

    assert (
        ap.debug_str()
        == "Date: 2020-01-01 10:00:00\nClinic: clinic111 (111)\nDoctor: doctor222 (222)\nSpecialty: specialty333 (333)\nType: xde\nBooked: Yes (ID: 123)\nAccount: N/A"
    )

    assert len(ap.notification_str()) == 7
