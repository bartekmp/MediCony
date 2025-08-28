"""
Tests for the matchers module functionality.

This module tests the appointment matching functions including exclusion checking,
single appointment matching, and date range matching functionality.
"""

import datetime

from src.id_value_util import IdValue
from src.medicover.appointment import Appointment
from src.medicover.matchers import (
    is_excluded,
    match_single_appointment,
    match_single_appointment_to_be_canceled,
    match_within_date_range,
)


class TestIsExcluded:
    """Test cases for the is_excluded function."""

    def test_is_excluded_no_exclusions(self):
        """Test that appointment is not excluded when exclusions is None or empty."""
        appointment = Appointment()
        appointment.doctor = IdValue(123, "Dr. Test")
        appointment.clinic = IdValue(456, "Test Clinic")

        # Test with None exclusions
        assert is_excluded(appointment, None) is False

        # Test with empty exclusions
        assert is_excluded(appointment, {}) is False

    def test_is_excluded_doctor_excluded(self):
        """Test that appointment is excluded when doctor is in exclusions."""
        appointment = Appointment()
        appointment.doctor = IdValue(123, "Dr. Test")
        appointment.clinic = IdValue(456, "Test Clinic")

        exclusions = {"doctor": ["123", "456"]}
        assert is_excluded(appointment, exclusions) is True

    def test_is_excluded_doctor_not_excluded(self):
        """Test that appointment is not excluded when doctor is not in exclusions."""
        appointment = Appointment()
        appointment.doctor = IdValue(123, "Dr. Test")
        appointment.clinic = IdValue(456, "Test Clinic")

        exclusions = {"doctor": ["789", "999"]}
        assert is_excluded(appointment, exclusions) is False

    def test_is_excluded_clinic_excluded(self):
        """Test that appointment is excluded when clinic is in exclusions."""
        appointment = Appointment()
        appointment.doctor = IdValue(123, "Dr. Test")
        appointment.clinic = IdValue(456, "Test Clinic")

        exclusions = {"clinic": ["456", "789"]}
        assert is_excluded(appointment, exclusions) is True

    def test_is_excluded_clinic_not_excluded(self):
        """Test that appointment is not excluded when clinic is not in exclusions."""
        appointment = Appointment()
        appointment.doctor = IdValue(123, "Dr. Test")
        appointment.clinic = IdValue(456, "Test Clinic")

        exclusions = {"clinic": ["123", "789"]}
        assert is_excluded(appointment, exclusions) is False

    def test_is_excluded_both_doctor_and_clinic_exclusions(self):
        """Test exclusions when both doctor and clinic exclusions are present."""
        appointment = Appointment()
        appointment.doctor = IdValue(123, "Dr. Test")
        appointment.clinic = IdValue(456, "Test Clinic")

        # Doctor excluded, clinic not
        exclusions = {"doctor": ["123"], "clinic": ["999"]}
        assert is_excluded(appointment, exclusions) is True

        # Clinic excluded, doctor not
        exclusions = {"doctor": ["999"], "clinic": ["456"]}
        assert is_excluded(appointment, exclusions) is True

        # Neither excluded
        exclusions = {"doctor": ["999"], "clinic": ["888"]}
        assert is_excluded(appointment, exclusions) is False

    def test_is_excluded_other_exclusion_types(self):
        """Test that other exclusion types don't affect the result."""
        appointment = Appointment()
        appointment.doctor = IdValue(123, "Dr. Test")
        appointment.clinic = IdValue(456, "Test Clinic")

        exclusions = {"specialty": ["789"], "other": ["123"]}
        assert is_excluded(appointment, exclusions) is False


class TestMatchSingleAppointmentToBeCanceled:
    """Test cases for the match_single_appointment_to_be_canceled function."""

    def test_match_found(self):
        """Test that matching appointment returns correct ID."""
        # Create appointment to be canceled
        appointment_data = {
            "appointmentDate": "2025-03-15T10:00:00",
            "clinic": {"id": "123", "name": "Test Clinic"},
            "doctor": {"id": "456", "name": "Dr. Test"},
            "specialty": {"id": "789", "name": "Cardiology"},
            "visitType": "Center",
        }
        appointment_to_cancel = Appointment(appointment_data)

        # Create server appointment list with matching appointment
        server_ap_list = [
            {
                "id": "app_001",
                "appointmentDate": "2025-03-15T10:00:00",
                "clinic": {"id": "123", "name": "Test Clinic"},
                "doctor": {"id": "456", "name": "Dr. Test"},
                "specialty": {"id": "789", "name": "Cardiology"},
                "visitType": "Center",
            },
            {
                "id": "app_002",
                "appointmentDate": "2025-03-16T11:00:00",
                "clinic": {"id": "124", "name": "Other Clinic"},
                "doctor": {"id": "457", "name": "Dr. Other"},
                "specialty": {"id": "790", "name": "Dermatology"},
                "visitType": "Center",
            },
        ]

        result = match_single_appointment_to_be_canceled(appointment_to_cancel, server_ap_list)
        assert result == "app_001"

    def test_match_not_found(self):
        """Test that non-matching appointment returns None."""
        # Create appointment to be canceled
        appointment_data = {
            "appointmentDate": "2025-03-15T10:00:00",
            "clinic": {"id": "123", "name": "Test Clinic"},
            "doctor": {"id": "456", "name": "Dr. Test"},
            "specialty": {"id": "789", "name": "Cardiology"},
            "visitType": "Center",
        }
        appointment_to_cancel = Appointment(appointment_data)

        # Create server appointment list with different appointments
        server_ap_list = [
            {
                "id": "app_001",
                "appointmentDate": "2025-03-16T10:00:00",  # Different date
                "clinic": {"id": "123", "name": "Test Clinic"},
                "doctor": {"id": "456", "name": "Dr. Test"},
                "specialty": {"id": "789", "name": "Cardiology"},
                "visitType": "Center",
            }
        ]

        result = match_single_appointment_to_be_canceled(appointment_to_cancel, server_ap_list)
        assert result is None

    def test_match_empty_server_list(self):
        """Test that empty server list returns None."""
        appointment_data = {
            "appointmentDate": "2025-03-15T10:00:00",
            "clinic": {"id": "123", "name": "Test Clinic"},
            "doctor": {"id": "456", "name": "Dr. Test"},
            "specialty": {"id": "789", "name": "Cardiology"},
            "visitType": "Center",
        }
        appointment_to_cancel = Appointment(appointment_data)

        result = match_single_appointment_to_be_canceled(appointment_to_cancel, [])
        assert result is None


class TestMatchSingleAppointment:
    """Test cases for the match_single_appointment function."""

    def create_test_appointment(self, specialty_id=789, clinic_id=123, doctor_id=456, date_time="2025-03-15T10:00:00"):
        """Helper method to create test appointment."""
        appointment_data = {
            "appointmentDate": date_time,
            "clinic": {"id": str(clinic_id), "name": "Test Clinic"},
            "doctor": {"id": str(doctor_id), "name": "Dr. Test"},
            "specialty": {"id": str(specialty_id), "name": "Test Specialty"},
            "visitType": "Center",
        }
        return Appointment(appointment_data)

    def test_exact_match(self):
        """Test exact matching of appointment."""
        appointment = self.create_test_appointment()
        appointments = [appointment]
        date_time = datetime.datetime.fromisoformat("2025-03-15T10:00:00")

        result = match_single_appointment(789, 123, 456, date_time, appointments)
        assert result == appointment

    def test_match_without_clinic_filter(self):
        """Test matching when clinic filter is None."""
        appointment = self.create_test_appointment(clinic_id=999)
        appointments = [appointment]
        date_time = datetime.datetime.fromisoformat("2025-03-15T10:00:00")

        result = match_single_appointment(789, None, 456, date_time, appointments)
        assert result == appointment

    def test_match_without_doctor_filter(self):
        """Test matching when doctor filter is None."""
        appointment = self.create_test_appointment(doctor_id=999)
        appointments = [appointment]
        date_time = datetime.datetime.fromisoformat("2025-03-15T10:00:00")

        result = match_single_appointment(789, 123, None, date_time, appointments)
        assert result == appointment

    def test_match_date_only(self):
        """Test matching by date only when exact_date_match=True, exact_time_match=False."""
        appointment = self.create_test_appointment(date_time="2025-03-15T14:30:00")
        appointments = [appointment]
        date_time = datetime.datetime.fromisoformat("2025-03-15T10:00:00")  # Same date, different time

        result = match_single_appointment(
            789, 123, 456, date_time, appointments, exact_time_match=False, exact_date_match=True
        )
        assert result == appointment

    def test_no_time_or_date_match_required(self):
        """Test matching when both exact_time_match and exact_date_match are False."""
        appointment = self.create_test_appointment(date_time="2025-03-16T14:30:00")  # Different date
        appointments = [appointment]
        date_time = datetime.datetime.fromisoformat("2025-03-15T10:00:00")

        result = match_single_appointment(
            789, 123, 456, date_time, appointments, exact_time_match=False, exact_date_match=False
        )
        assert result == appointment

    def test_no_match_different_specialty(self):
        """Test no match when specialty doesn't match."""
        appointment = self.create_test_appointment(specialty_id=999)
        appointments = [appointment]
        date_time = datetime.datetime.fromisoformat("2025-03-15T10:00:00")

        result = match_single_appointment(789, 123, 456, date_time, appointments)
        assert result is None

    def test_no_match_different_clinic(self):
        """Test no match when clinic filter doesn't match."""
        appointment = self.create_test_appointment(clinic_id=999)
        appointments = [appointment]
        date_time = datetime.datetime.fromisoformat("2025-03-15T10:00:00")

        result = match_single_appointment(789, 123, 456, date_time, appointments)
        assert result is None

    def test_no_match_different_doctor(self):
        """Test no match when doctor filter doesn't match."""
        appointment = self.create_test_appointment(doctor_id=999)
        appointments = [appointment]
        date_time = datetime.datetime.fromisoformat("2025-03-15T10:00:00")

        result = match_single_appointment(789, 123, 456, date_time, appointments)
        assert result is None

    def test_no_match_different_time_and_exact_time_only(self):
        """Test no match when time doesn't match and we want exact time match only."""
        appointment = self.create_test_appointment(date_time="2025-03-15T14:00:00")
        appointments = [appointment]
        date_time = datetime.datetime.fromisoformat("2025-03-15T10:00:00")

        # When exact_time_match=True and exact_date_match=False, only exact time should matter
        result = match_single_appointment(
            789, 123, 456, date_time, appointments, exact_time_match=True, exact_date_match=False
        )
        assert result is None

    def test_match_different_time_but_same_date_with_exact_date_match(self):
        """Test match when time is different but date matches and exact_date_match=True."""
        appointment = self.create_test_appointment(date_time="2025-03-15T14:00:00")
        appointments = [appointment]
        date_time = datetime.datetime.fromisoformat("2025-03-15T10:00:00")

        # When both exact_time_match=True and exact_date_match=True (default),
        # it should match if EITHER time OR date matches
        result = match_single_appointment(789, 123, 456, date_time, appointments)
        assert result == appointment

    def test_no_match_different_date_and_exact_date_only(self):
        """Test no match when date doesn't match and we want exact date match only."""
        appointment = self.create_test_appointment(date_time="2025-03-16T10:00:00")
        appointments = [appointment]
        date_time = datetime.datetime.fromisoformat("2025-03-15T10:00:00")

        # When exact_time_match=False and exact_date_match=True, only exact date should matter
        result = match_single_appointment(
            789, 123, 456, date_time, appointments, exact_time_match=False, exact_date_match=True
        )
        assert result is None

    def test_multiple_appointments_first_match_returned(self):
        """Test that first matching appointment is returned when multiple matches exist."""
        appointment1 = self.create_test_appointment()
        appointment2 = self.create_test_appointment()
        appointments = [appointment1, appointment2]
        date_time = datetime.datetime.fromisoformat("2025-03-15T10:00:00")

        result = match_single_appointment(789, 123, 456, date_time, appointments)
        assert result == appointment1

    def test_empty_appointments_list(self):
        """Test with empty appointments list."""
        date_time = datetime.datetime.fromisoformat("2025-03-15T10:00:00")

        result = match_single_appointment(789, 123, 456, date_time, [])
        assert result is None


class TestMatchWithinDateRange:
    """Test cases for the match_within_date_range function."""

    def create_test_appointment(self, specialty_id=789, clinic_id=123, doctor_id=456, date_time="2025-03-15T10:00:00"):
        """Helper method to create test appointment."""
        appointment_data = {
            "appointmentDate": date_time,
            "clinic": {"id": str(clinic_id), "name": "Test Clinic"},
            "doctor": {"id": str(doctor_id), "name": "Dr. Test"},
            "specialty": {"id": str(specialty_id), "name": "Test Specialty"},
            "visitType": "Center",
        }
        return Appointment(appointment_data)

    def test_match_within_date_range(self):
        """Test matching appointments within date range."""
        appointments = [
            self.create_test_appointment(date_time="2025-03-14T10:00:00"),  # Before range
            self.create_test_appointment(date_time="2025-03-15T10:00:00"),  # In range
            self.create_test_appointment(date_time="2025-03-16T10:00:00"),  # In range
            self.create_test_appointment(date_time="2025-03-18T10:00:00"),  # After range
        ]

        start_date = datetime.date(2025, 3, 15)
        end_date = datetime.date(2025, 3, 17)

        result = match_within_date_range(789, 123, 456, start_date, end_date, appointments)
        assert len(result) == 2
        assert result[0].date_time.date() == datetime.date(2025, 3, 15)
        assert result[1].date_time.date() == datetime.date(2025, 3, 16)

    def test_match_without_end_date(self):
        """Test matching when end_date is None (should use datetime.date.max)."""
        appointments = [
            self.create_test_appointment(date_time="2025-03-14T10:00:00"),  # Before range
            self.create_test_appointment(date_time="2025-03-15T10:00:00"),  # In range
            self.create_test_appointment(date_time="2025-12-31T10:00:00"),  # In range (far future)
        ]

        start_date = datetime.date(2025, 3, 15)

        result = match_within_date_range(789, 123, 456, start_date, None, appointments)
        assert len(result) == 2
        assert result[0].date_time.date() == datetime.date(2025, 3, 15)
        assert result[1].date_time.date() == datetime.date(2025, 12, 31)

    def test_match_without_clinic_filter(self):
        """Test matching when clinic filter is None."""
        appointments = [
            self.create_test_appointment(clinic_id=999, date_time="2025-03-15T10:00:00"),
            self.create_test_appointment(clinic_id=888, date_time="2025-03-16T10:00:00"),
        ]

        start_date = datetime.date(2025, 3, 15)
        end_date = datetime.date(2025, 3, 17)

        result = match_within_date_range(789, None, 456, start_date, end_date, appointments)
        assert len(result) == 2

    def test_match_without_doctor_filter(self):
        """Test matching when doctor filter is None."""
        appointments = [
            self.create_test_appointment(doctor_id=999, date_time="2025-03-15T10:00:00"),
            self.create_test_appointment(doctor_id=888, date_time="2025-03-16T10:00:00"),
        ]

        start_date = datetime.date(2025, 3, 15)
        end_date = datetime.date(2025, 3, 17)

        result = match_within_date_range(789, 123, None, start_date, end_date, appointments)
        assert len(result) == 2

    def test_no_matches_different_specialty(self):
        """Test no matches when specialty doesn't match."""
        appointments = [
            self.create_test_appointment(specialty_id=999, date_time="2025-03-15T10:00:00"),
        ]

        start_date = datetime.date(2025, 3, 15)
        end_date = datetime.date(2025, 3, 17)

        result = match_within_date_range(789, 123, 456, start_date, end_date, appointments)
        assert len(result) == 0

    def test_no_matches_different_clinic(self):
        """Test no matches when clinic filter doesn't match."""
        appointments = [
            self.create_test_appointment(clinic_id=999, date_time="2025-03-15T10:00:00"),
        ]

        start_date = datetime.date(2025, 3, 15)
        end_date = datetime.date(2025, 3, 17)

        result = match_within_date_range(789, 123, 456, start_date, end_date, appointments)
        assert len(result) == 0

    def test_no_matches_different_doctor(self):
        """Test no matches when doctor filter doesn't match."""
        appointments = [
            self.create_test_appointment(doctor_id=999, date_time="2025-03-15T10:00:00"),
        ]

        start_date = datetime.date(2025, 3, 15)
        end_date = datetime.date(2025, 3, 17)

        result = match_within_date_range(789, 123, 456, start_date, end_date, appointments)
        assert len(result) == 0

    def test_no_matches_outside_date_range(self):
        """Test no matches when all appointments are outside date range."""
        appointments = [
            self.create_test_appointment(date_time="2025-03-14T10:00:00"),  # Before range
            self.create_test_appointment(date_time="2025-03-18T10:00:00"),  # After range
        ]

        start_date = datetime.date(2025, 3, 15)
        end_date = datetime.date(2025, 3, 17)

        result = match_within_date_range(789, 123, 456, start_date, end_date, appointments)
        assert len(result) == 0

    def test_edge_case_start_date_equals_end_date(self):
        """Test edge case when start_date equals end_date."""
        appointments = [
            self.create_test_appointment(date_time="2025-03-15T10:00:00"),
            self.create_test_appointment(date_time="2025-03-16T10:00:00"),
        ]

        start_date = datetime.date(2025, 3, 15)
        end_date = datetime.date(2025, 3, 15)

        result = match_within_date_range(789, 123, 456, start_date, end_date, appointments)
        assert len(result) == 1
        assert result[0].date_time.date() == datetime.date(2025, 3, 15)

    def test_empty_appointments_list(self):
        """Test with empty appointments list."""
        start_date = datetime.date(2025, 3, 15)
        end_date = datetime.date(2025, 3, 17)

        result = match_within_date_range(789, 123, 456, start_date, end_date, [])
        assert len(result) == 0
