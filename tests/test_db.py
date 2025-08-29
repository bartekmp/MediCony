"""
Tests for the database functionality in MediCony.

This module contains tests for the DbClient and DbLogic classes, which handle
database operations for appointments and watches using PostgreSQL and SQLAlchemy.
It verifies database CRUD operations, data integrity, and proper handling of appointment and watch data.
"""

import datetime
from typing import Generator

import pytest
import pytz
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.database import MedicoverDbClient
from src.database.medicover_db import MedicoverDbLogic


def flatten_exclusions(exclusions_dict):
    """Helper function to flatten exclusions dictionary to string format."""
    if not exclusions_dict:
        return ""

    parts = []
    for key, values in exclusions_dict.items():
        if isinstance(values, list):
            values_str = ",".join(values)
        else:
            values_str = str(values)
        parts.append(f"{key}:{values_str}")

    return ";".join(parts)


from src.id_value_util import IdValue
from src.medicover.appointment import Appointment
from src.medicover.watch import Watch
from src.models import Base, MedicoverAppointmentModel, MedicoverWatchModel, MedicineModel


class SqliteDbLogic(MedicoverDbLogic):
    """Test version of DbLogic that uses SQLite for testing."""

    def __init__(self, test_db_path: str = ":memory:"):
        # Override parent init to use SQLite for testing
        self._lock = self.__class__.__dict__.get("_lock", None) or __import__("threading").RLock()

        # Use SQLite for testing
        if test_db_path == ":memory:":
            database_url = "sqlite:///:memory:"
        else:
            database_url = f"sqlite:///{test_db_path}"

        try:
            # Create engine
            self.engine = create_engine(database_url, echo=False)

            # Create session factory
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

            # Create tables
            Base.metadata.create_all(bind=self.engine)

            # Don't call clear_db to avoid timezone issues in tests
        except Exception as e:
            raise Exception(f"Failed to connect to test SQLite database: {e}")


class SqliteDbClient(MedicoverDbClient):
    """Test version of DbClient that uses SqliteDbLogic."""

    def __init__(self, test_db_path: str = ":memory:"):
        # Override to use SqliteDbLogic instead of DbLogic
        self.db = SqliteDbLogic(test_db_path)


@pytest.fixture
def db() -> Generator[SqliteDbLogic, None, None]:
    """
    Fixture providing a clean in-memory database instance for testing.

    Yields:
        SqliteDbLogic: A database instance with tables cleared for testing.
    """
    db_instance = SqliteDbLogic(":memory:")
    # Clear any existing data
    with db_instance.get_session() as session:
        session.execute(text("DELETE FROM appointment"))
        session.execute(text("DELETE FROM watch"))
        session.execute(text("DELETE FROM medicine"))
        session.commit()
    yield db_instance


@pytest.fixture
def db_client() -> Generator[SqliteDbClient, None, None]:
    """
    Fixture providing a clean DbClient instance with in-memory database for testing.

    Yields:
        TestDbClient: A client instance with a clean database for testing.
    """
    db_client_instance = SqliteDbClient(":memory:")
    # Clear any existing data
    with db_client_instance.db.get_session() as session:
        session.execute(text("DELETE FROM appointment"))
        session.execute(text("DELETE FROM watch"))
        session.execute(text("DELETE FROM medicine"))
        session.commit()
    yield db_client_instance


def test_clear_db(db: SqliteDbLogic) -> None:
    """
    Test that clear_db method removes only past appointments.

    This test verifies that the clear_db method removes only appointments with dates
    in the past, while keeping future appointments.

    Args:
        db: The database fixture.
    """
    # Arrange
    now = datetime.datetime.now(pytz.timezone("Europe/Warsaw"))
    past_date = now - datetime.timedelta(days=1)
    future_date = now + datetime.timedelta(days=1)

    with db.get_session() as session:
        # Add past appointment
        past_appointment = MedicoverAppointmentModel(
            clinic=1, doctor=11, date=past_date, specialty=23, visitType="Center", bookingString="booking1"
        )
        session.add(past_appointment)

        # Add future appointment
        future_appointment = MedicoverAppointmentModel(
            clinic=2, doctor=22, date=future_date, specialty=24, visitType="Center", bookingString="booking2"
        )
        session.add(future_appointment)
        session.commit()

    # Act
    db.clear_db()

    # Assert
    with db.get_session() as session:
        appointments = session.query(MedicoverAppointmentModel).all()
        assert len(appointments) == 1, "Only one appointment (future) should remain"
        # Convert to actual date value for comparison
        appointment_date = appointments[0].__dict__["date"]
        if appointment_date >= now.replace(tzinfo=None):
            assert True, "The remaining appointment should be the future one"
        else:
            assert False, "The remaining appointment should be the future one"
    clinicId = 1
    doctorId = 2

    # Create appointment records
    appointment1 = MedicoverAppointmentModel(
        clinic=clinicId,
        doctor=doctorId,
        date=datetime.datetime(2023, 10, 10, 10, 0, 0),
        specialty=3,
        visitType="visitType1",
        bookingString="bookingString1",
        bookingIdentifier=1,
    )
    appointment2 = MedicoverAppointmentModel(
        clinic=11,
        doctor=22,
        date=datetime.datetime(2023, 10, 11, 10, 0, 0),
        specialty=33,
        visitType="visitType2",
        bookingString="bookingString2",
        bookingIdentifier=None,
    )

    with db.get_session() as session:
        session.add(appointment1)
        session.add(appointment2)
        session.commit()

    booked_appointments = db.get_booked_appointments()
    assert len(booked_appointments) == 1
    assert booked_appointments[0][1] == clinicId
    assert booked_appointments[0][2] == doctorId


def test_add_appointment_history(db):
    clinic = IdValue(155, "clinic1")
    doctor = IdValue(555, "doctor1")

    appointment = Appointment.initialize(
        clinic=clinic,
        doctor=doctor,
        date_time="2023-10-10 10:00:00",
        specialty=IdValue(23, "specialty1"),
        visit_type="visitType1",
        booking_string="bookingString1",
        booking_identifier=1,
    )

    db.add_appointment_history(appointment)

    with db.get_session() as session:
        appointments = session.query(MedicoverAppointmentModel).filter_by(clinic=clinic.id, doctor=doctor.id).all()
        assert len(appointments) == 1
        assert appointments[0].clinic == clinic.id
        assert appointments[0].doctor == doctor.id


def test_update_appointment(db):
    clinic = IdValue(155, "clinic1")
    doctor = IdValue(555, "doctor1")
    specialty = IdValue(23, "specialty1")
    date_time = datetime.datetime.fromisoformat("2023-10-10 10:00:00")

    # Create initial appointment
    appointment_model = MedicoverAppointmentModel(
        clinic=clinic.id,
        doctor=doctor.id,
        date=date_time,
        specialty=specialty.id,
        visitType="visitType1",
        bookingString="bookingString1",
        bookingIdentifier=0,
    )

    with db.get_session() as session:
        session.add(appointment_model)
        session.commit()

    appointment = Appointment.initialize(
        clinic=clinic,
        doctor=doctor,
        date_time="2023-10-10 10:00:00",
        specialty=specialty,
        visit_type="visitType1",
        booking_string="bookingString1",
        booking_identifier=1234567,
    )

    db.update_appointment(appointment)

    with db.get_session() as session:
        appointments = session.query(MedicoverAppointmentModel).filter_by(clinic=clinic.id, doctor=doctor.id).all()
        assert len(appointments) == 1
        assert appointments[0].bookingIdentifier == "1234567"


def test_remove_appointment(db):
    # Create appointment
    appointment_model = MedicoverAppointmentModel(
        clinic=111,
        doctor=222,
        date=datetime.datetime(2023, 10, 10, 10, 0, 0),
        specialty=333,
        visitType="visitType1",
        bookingString="bookingString1",
        bookingIdentifier=1,
    )

    with db.get_session() as session:
        session.add(appointment_model)
        session.commit()
        appointment_id = appointment_model.id

    db.remove_appointment(appointment_id)

    with db.get_session() as session:
        appointments = session.query(MedicoverAppointmentModel).filter_by(id=appointment_id).all()
        assert len(appointments) == 0


def test_save_watch_with_not_all_fields(db):
    region = 200
    specialty = 9
    watch = Watch.from_tuple(
        (
            0,
            region,
            "uuu",
            [specialty],
            1337,
            2137,
            "2023-10-10",
            "2023-10-11",
            "09:00:00-17:00:00",
            True,
        )
    )

    db.save_watch(watch)

    with db.get_session() as session:
        watches = session.query(MedicoverWatchModel).filter_by(region=region, specialty=str(specialty)).all()
        assert len(watches) == 1
        assert watches[0].region == region
        assert watches[0].specialty == str(specialty)


def test_remove_watch(db):
    # Create watch
    watch_model = MedicoverWatchModel(
        region=1,
        city="abc",
        specialty="2",
        doctor=3,
        clinic=4,
        startDate=datetime.date(2023, 10, 10),
        endDate=datetime.date(2023, 10, 11),
        timeRange="09:00:00-17:00:00",
        autobook=True,
        exclusions="doctor:123;clinic:456",
        type="Standard",
    )

    with db.get_session() as session:
        session.add(watch_model)
        session.commit()
        watch_id = watch_model.id

    assert db.remove_watch(watch_id)

    with db.get_session() as session:
        watches = session.query(MedicoverWatchModel).filter_by(id=watch_id).all()
        assert len(watches) == 0


def test_get_watches(db):
    # Create watches
    watch1 = MedicoverWatchModel(
        region=1,
        city="ppp",
        specialty="2",
        doctor=3,
        clinic=4,
        startDate=datetime.date(2023, 10, 10),
        endDate=datetime.date(2023, 10, 11),
        timeRange="09:00-17:00",
        autobook=True,
        exclusions="doctor:123;clinic:456",
        type="Standard",
    )
    watch2 = MedicoverWatchModel(
        region=11,
        city="ooo",
        specialty="22",
        doctor=33,
        clinic=44,
        startDate=datetime.date(2023, 10, 12),
        endDate=datetime.date(2023, 10, 13),
        timeRange="10:00-18:00",
        autobook=True,
        exclusions=None,
        type="DiagnosticProcedure",
    )

    with db.get_session() as session:
        session.add(watch1)
        session.add(watch2)
        session.commit()

    watches = db.get_watches()
    assert len(watches) == 2
    assert watches[0][1] == 1
    assert watches[1][1] == 11
    assert watches[0][10] == "doctor:123;clinic:456"
    assert watches[1][10] is None
    assert watches[0][11] == "Standard"
    assert watches[1][11] == "DiagnosticProcedure"


def test_dbclient_get_watches(db_client):
    # Create watches via DbLogic
    watch1 = MedicoverWatchModel(
        region=1,
        city="ttt",
        specialty="2",
        doctor=3,
        clinic=4,
        startDate=datetime.date(2023, 10, 10),
        endDate=datetime.date(2023, 10, 11),
        timeRange="09:00-17:00",
        autobook=True,
        exclusions="doctor:123,999;clinic:456",
        type="Standard",
    )
    watch2 = MedicoverWatchModel(
        region=11,
        city="k",
        specialty="22",
        doctor=33,
        clinic=44,
        startDate=datetime.date(2023, 10, 12),
        endDate=datetime.date(2023, 10, 13),
        timeRange="10:00-18:00",
        autobook=True,
        exclusions="clinic:888",
        type="DiagnosticProcedure",
    )

    with db_client.db.get_session() as session:
        session.add(watch1)
        session.add(watch2)
        session.commit()

    watches = db_client.get_watches()
    assert len(watches) == 2
    assert watches[0].region.id == 1
    assert watches[1].region.id == 11
    assert watches[0].city == "ttt"
    assert watches[1].city == "k"
    assert watches[0].type == "Standard"
    assert watches[1].type == "DiagnosticProcedure"
    assert watches[0].exclusions == {"doctor": ["123", "999"], "clinic": ["456"]}
    assert watches[1].exclusions == {"clinic": ["888"]}
    assert flatten_exclusions(watches[0].exclusions) == "doctor:123,999;clinic:456"
    assert flatten_exclusions(watches[1].exclusions) == "clinic:888"


def test_dbclient_remove_watch(db_client):
    # Create watch
    watch_model = MedicoverWatchModel(
        region=1,
        city="Berlin",
        specialty="2",
        doctor=3,
        clinic=4,
        startDate=datetime.date(2023, 10, 10),
        endDate=datetime.date(2023, 10, 11),
        timeRange="09:00-17:00",
        autobook=True,
        exclusions=None,
        type="Standard",
    )

    with db_client.db.get_session() as session:
        session.add(watch_model)
        session.commit()
        watch_id = watch_model.id

    assert db_client.remove_watch(watch_id)

    with db_client.db.get_session() as session:
        watches = session.query(MedicoverWatchModel).filter_by(id=watch_id).all()
        assert len(watches) == 0


def test_dbclient_save_watch(db_client):
    region = 200
    specialty = 9
    watch = Watch.from_tuple(
        (
            0,
            region,
            "Aszchabad",
            [specialty],
            1337,
            2137,
            "2023-10-10",
            "2023-10-11",
            "09:00:00-17:00:00",
            True,
            "doctor:123,456;clinic:789,1011",
            "DiagnosticProcedure",
        )
    )

    db_client.save_watch(watch)

    with db_client.db.get_session() as session:
        watches = session.query(MedicoverWatchModel).filter_by(region=region, specialty=str(specialty)).all()
        assert len(watches) == 1
        assert watches[0].region == region
        assert watches[0].city == "Aszchabad"
        assert watches[0].specialty == str(specialty)
        assert watches[0].exclusions == "doctor:123,456;clinic:789,1011"
        assert watches[0].type == "DiagnosticProcedure"


def test_dbclient_save_watch_multiple_specialties(db_client):
    region = 200
    specialty = [9, 10, 11, 12]
    watch = Watch.from_tuple(
        (
            0,
            region,
            "Aszchabad",
            specialty,
            1337,
            2137,
            "2023-10-10",
            "2023-10-11",
            "09:00:00-17:00:00",
            True,
            None,
            "DiagnosticProcedure",
        )
    )

    db_client.save_watch(watch)
    specialty_str = ",".join([str(s) for s in specialty])

    with db_client.db.get_session() as session:
        watches = session.query(MedicoverWatchModel).filter_by(region=region, specialty=specialty_str).all()
        assert len(watches) == 1
        assert watches[0].region == region
        assert watches[0].city == "Aszchabad"
        assert watches[0].specialty == specialty_str
        assert watches[0].exclusions is None
        assert watches[0].type == "DiagnosticProcedure"


def test_dbclient_update_appointment(db_client):
    clinic = IdValue(155, "clinic1")
    doctor = IdValue(555, "doctor1")
    specialty = IdValue(23, "specialty1")
    date_time = datetime.datetime.fromisoformat("2023-10-10 10:00:00")

    # Create initial appointment
    appointment_model = MedicoverAppointmentModel(
        clinic=clinic.id,
        doctor=doctor.id,
        date=date_time,
        specialty=specialty.id,
        visitType="visitType1",
        bookingString="bookingString1",
        bookingIdentifier=None,
    )

    with db_client.db.get_session() as session:
        session.add(appointment_model)
        session.commit()

    appointment = Appointment.initialize(
        clinic=clinic,
        doctor=doctor,
        date_time="2023-10-10 10:00:00",
        specialty=specialty,
        visit_type="visitType1",
        booking_string="bookingString1",
        booking_identifier=1994567,
    )

    db_client.update_appointment(appointment)

    with db_client.db.get_session() as session:
        appointments = session.query(MedicoverAppointmentModel).filter_by(clinic=clinic.id, doctor=doctor.id).all()
        assert len(appointments) == 1
        assert appointments[0].bookingIdentifier == "1994567"


def test_dbclient_save_appointments_and_filter_old(db_client):
    clinic = IdValue(155, "clinic1")
    doctor = IdValue(555, "doctor1")
    specialty = IdValue(23, "specialty1")

    appointment1 = Appointment.initialize(
        clinic=clinic,
        doctor=doctor,
        date_time="2023-10-10 10:00:00",
        specialty=specialty,
        visit_type="visitType1",
        booking_string="bookingString1",
        booking_identifier=1234567,
    )

    appointment2 = Appointment.initialize(
        clinic=clinic,
        doctor=doctor,
        date_time="2023-10-11 10:00:00",
        specialty=specialty,
        visit_type="visitType2",
        booking_string="bookingString2",
        booking_identifier=1234568,
    )

    new_appointments = db_client.save_appointments_and_filter_old([appointment1, appointment2])

    assert len(new_appointments) == 2

    with db_client.db.get_session() as session:
        appointments = session.query(MedicoverAppointmentModel).filter_by(clinic=clinic.id, doctor=doctor.id).all()
        assert len(appointments) == 2
        assert appointments[0].clinic == clinic.id
        assert appointments[0].doctor == doctor.id
        assert appointments[1].clinic == clinic.id
        assert appointments[1].doctor == doctor.id


def test_dbclient_list_booked_appointments(db_client):
    # Create appointments
    appointment1 = MedicoverAppointmentModel(
        clinic=234,
        doctor=345,
        date=datetime.datetime(2025, 4, 10, 10, 0, 0),
        specialty=456,
        visitType="visitType1",
        bookingString="bookingString1",
        bookingIdentifier=123123123,
    )
    appointment2 = MedicoverAppointmentModel(
        clinic=4,
        doctor=3,
        date=datetime.datetime(2025, 4, 10, 10, 0, 0),
        specialty=2,
        visitType="visitType1",
        bookingString="bookingString2",
        bookingIdentifier=1,
    )
    appointment3 = MedicoverAppointmentModel(
        clinic=111,
        doctor=222,
        date=datetime.datetime(2025, 4, 10, 10, 0, 0),
        specialty=333,
        visitType="visitType1",
        bookingString="bookingString3",
        bookingIdentifier=None,
    )

    with db_client.db.get_session() as session:
        session.add(appointment1)
        session.add(appointment2)
        session.add(appointment3)
        session.commit()

    booked_aps = db_client.get_booked_appointments()
    assert len(booked_aps) == 2


def test_edit_watch_updates_fields(db_client):
    # Insert a watch
    region = 1
    specialty = [9]
    watch = Watch.from_tuple(
        (
            0,
            region,
            "OldCity",
            specialty,
            1337,
            2137,
            "2023-10-10",
            "2023-10-11",
            "09:00:00-17:00:00",
            False,
            None,
            "Standard",
        )
    )
    db_client.save_watch(watch)

    with db_client.db.get_session() as session:
        watch_record = session.query(MedicoverWatchModel).filter_by(region=region, city="OldCity").first()
        watch_id = watch_record.id

    # Edit the watch
    db_client.update_watch(
        watch_id=watch_id,
        city="NewCity",
        clinic_id=2024,
        start_date=datetime.date(2024, 1, 1),
        end_date=datetime.date(2024, 12, 31),
        time_range="08:00:00-16:00:00",
        exclusions="doctor:123;clinic:456",
        auto_book=True,
    )

    with db_client.db.get_session() as session:
        updated = session.query(MedicoverWatchModel).filter_by(id=watch_id).first()
        assert updated.city == "NewCity"
        assert updated.clinic == 2024
        assert updated.startDate == datetime.date(2024, 1, 1)
        assert updated.endDate == datetime.date(2024, 12, 31)
        assert updated.timeRange == "08:00:00-16:00:00"
        assert updated.autobook is True
        assert updated.exclusions == "doctor:123;clinic:456"


def test_edit_watch_no_fields_to_update(db_client):
    # Insert a watch
    region = 2
    specialty = [10]
    watch = Watch.from_tuple(
        (
            0,
            region,
            "City",
            specialty,
            555,
            666,
            "2023-10-10",
            "2023-10-11",
            "09:00:00-17:00:00",
            False,
            None,
            "Standard",
        )
    )
    db_client.save_watch(watch)

    with db_client.db.get_session() as session:
        watch_record = session.query(MedicoverWatchModel).filter_by(region=region, city="City").first()
        watch_id = watch_record.id

    # Should not raise or update anything if no fields are provided
    db_client.update_watch(watch_id)

    with db_client.db.get_session() as session:
        updated = session.query(MedicoverWatchModel).filter_by(id=watch_id).first()
        assert updated.city == "City"
        assert updated.clinic == 555
