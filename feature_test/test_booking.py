import asyncio
import random
from datetime import date, datetime

from src.database import MedicoverDbClient
from src.medicover.api_client import MediAPI
from src.medicover.watch import WatchType

"""
Tests for booking appointments using the MediAPI client.
WARNING: LAUNCH CAREFULLY! - these tests will book real appointments on your account and may cancel them.
These tests require a valid MEDICOVER_USERDATA environment variable to be set.
"""


async def test_find_real_examination_appointments(
    skip_if_no_real_userdata, env_vars, db_client: MedicoverDbClient, api_client: MediAPI
):
    # Find real examination appointments to "Punkt pobrań" in Gdańsk since today
    examination_specialty_id = 52106  # Specialty ID for "Punkt pobrań" in Gdańsk
    local_region_id = 200  # Region ID for Gdańsk
    local_clinic_ids = [56156, 21950]  # Clinic IDs in Gdańsk that have "Punkt pobrań"
    args = {
        "region": local_region_id,
        "city": "Gdańsk",
        "specialty": examination_specialty_id,
        "clinic": None,
        "date": str(date.today().isoformat()),
        "doctor": None,
        "examination": False,  # "Punkt pobrań" is a STANDARD type for some reason in their API
    }
    appointments = await api_client.find_appointments(
        args["region"],
        args["city"],
        args["specialty"],
        args["clinic"],
        args["date"],
        args["doctor"],
        WatchType.EXAMINATION if args["examination"] else WatchType.STANDARD,
    )

    assert appointments is not None, "No appointments found"
    assert len(appointments) > 0, "No appointments found"

    appt = appointments[0]
    assert (
        appt.booking_string
    ), "First available appointment does not have a booking string"  # A booking string is required to book an appointment
    assert appt.visit_type == "Center"
    assert (
        appt.specialty.id == examination_specialty_id
    ), f"First available appointment does not have the expected specialty ID {examination_specialty_id}"
    assert (
        "punkt pobrań" in str(appt.doctor.value).lower()
    ), "First available appointment does not have a artificial 'doctor' with 'punkt pobrań' in their name"
    assert (
        appt.clinic.id in local_clinic_ids
    ), f"First available appointment does not have a clinic ID in the expected list {local_clinic_ids}"


async def test_find_fake_appointment(skip_if_no_real_userdata, env_vars, db_client: MedicoverDbClient, api_client: MediAPI):
    # Check if the API correctly handles a fake specialty ID
    examination_specialty_id = random.randint(5000, 9000)  # Fake specialty ID for testing purposes
    local_region_id = 200  # Region ID for Gdańsk
    args = {
        "region": local_region_id,
        "city": "Gdańsk",
        "specialty": examination_specialty_id,
        "clinic": None,
        "date": str(date.today().isoformat()),
        "doctor": None,
        "examination": False,
    }
    appointments = await api_client.find_appointments(
        args["region"],
        args["city"],
        args["specialty"],
        args["clinic"],
        args["date"],
        args["doctor"],
        WatchType.EXAMINATION if args["examination"] else WatchType.STANDARD,
    )

    assert appointments is not None, "No appointments found"
    assert len(appointments) == 0, "Some appointments found, but expected none for the fake specialty ID"


async def test_find_manually_and_book_real_examination(
    skip_if_no_real_userdata, env_vars, db_client: MedicoverDbClient, api_client: MediAPI
):
    # Manually find and BOOK a real examination appointment to "Punkt pobrań" in Gdańsk since today
    examination_specialty_id = 52106  # Specialty ID for "Punkt pobrań" in Gdańsk
    local_region_id = 200  # Region ID for Gdańsk
    local_clinic_ids = [56156, 21950]  # Clinic IDs in Gdańsk that have "Punkt pobrań"
    args = {
        "region": local_region_id,
        "city": "Gdańsk",
        "specialty": examination_specialty_id,
        "clinic": None,
        "date": str(date.today().isoformat()),
        "doctor": None,
        "examination": False,  # "Punkt pobrań" is a STANDARD type for some reason in their API
    }
    appointments = await api_client.find_appointments(
        args["region"],
        args["city"],
        args["specialty"],
        args["clinic"],
        args["date"],
        args["doctor"],
        WatchType.EXAMINATION if args["examination"] else WatchType.STANDARD,
    )

    assert appointments is not None, "No appointments found"
    assert len(appointments) > 0, "No appointments found"

    appt = appointments[0]
    assert (
        appt.booking_string
    ), "First available appointment does not have a booking string"  # A booking string is required to book an appointment
    assert appt.visit_type == "Center"
    assert (
        appt.specialty.id == examination_specialty_id
    ), f"First available appointment does not have the expected specialty ID {examination_specialty_id}"
    assert (
        "punkt pobrań" in str(appt.doctor.value).lower()
    ), "First available appointment does not have a artificial 'doctor' with 'punkt pobrań' in their name"
    assert (
        appt.clinic.id in local_clinic_ids
    ), f"First available appointment does not have a clinic ID in the expected list {local_clinic_ids}"

    await asyncio.sleep(5)  # Slow down to avoid hitting rate limits
    # Send the booking request for the first available appointment
    booked_appt = await api_client.book_appointment(
        appt, WatchType.EXAMINATION if args["examination"] else WatchType.STANDARD
    )

    assert booked_appt is not None, "No appointment booked"
    assert booked_appt.booking_identifier is not None, "Booked appointment does not have a booking identifier"

    await asyncio.sleep(15)  # Slow down to avoid hitting rate limits
    # Cancel the appointment to clean up
    assert await api_client.cancel_appointment(booked_appt)


async def test_auto_find_and_book_real_examination(
    skip_if_no_real_userdata, env_vars, db_client: MedicoverDbClient, api_client: MediAPI
):
    # Automatically find and BOOK a real examination appointment to "Punkt pobrań" in Gdańsk since today
    examination_specialty_id = 52106  # Specialty ID for "Punkt pobrań" in Gdańsk
    local_region_id = 200  # Region ID for Gdańsk
    local_clinic_ids = [56156, 21950]  # Clinic IDs in Gdańsk that have "Punkt pobrań"
    args = {
        "region": local_region_id,
        "city": "Gdańsk",
        "specialty": examination_specialty_id,
        "clinic": None,
        "date": datetime.today(),
        "doctor": None,
        "examination": False,  # "Punkt pobrań" is a STANDARD type for some reason in their API
    }

    # Try to find and book a first available appointment automatically
    booked_appt = await api_client.find_and_book_appointment(
        args["region"],
        args["city"],
        args["specialty"],
        args["clinic"],
        args["date"],
        args["doctor"],
        WatchType.EXAMINATION if args["examination"] else WatchType.STANDARD,
        exact_time_match=False,  # Allow for a first available appointment, not matching the exact time and hour
        exact_date_match=False,  # Allow for a first available appointment, not matching the exact date
    )

    assert booked_appt is not None, "No appointment booked"
    assert booked_appt.booking_identifier is not None, "Booked appointment does not have a booking identifier"
    assert booked_appt.booking_string, "First available appointment does not have a booking string"
    assert booked_appt.visit_type == "Center"
    assert (
        booked_appt.specialty.id == examination_specialty_id
    ), f"First available appointment does not have the expected specialty ID {examination_specialty_id}"
    assert (
        "punkt pobrań" in str(booked_appt.doctor.value).lower()
    ), "First available appointment does not have a artificial 'doctor' with 'punkt pobrań' in their name"
    assert (
        booked_appt.clinic.id in local_clinic_ids
    ), f"First available appointment does not have a clinic ID in the expected list {local_clinic_ids}"

    await asyncio.sleep(15)  # Slow down to avoid hitting rate limits
    # Cancel the appointment to clean up
    assert await api_client.cancel_appointment(booked_appt)
