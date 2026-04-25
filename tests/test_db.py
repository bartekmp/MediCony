"""
Tests for the database functionality in MediCony.

This module contains tests for the DbClient class, which handles
database operations for appointments and watches using PostgreSQL and SQLAlchemy.
It verifies database CRUD operations, data integrity, and proper handling of appointment and watch data.
"""

import datetime
import threading
from typing import Generator

import pytest
import pytz
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.database.medicover_db import MedicoverDbClient
from src.id_value_util import IdValue
from src.medicover.appointment import Appointment
from src.medicover.watch import Watch, WatchTimeRange, WatchType, flatten_exclusions, parse_exclusions
from src.models import (
    Base,
    MedicoverAppointmentModel,
    MedicoverWatchModel,
)


class SqliteDbClient(MedicoverDbClient):
    """In-memory SQLite stand-in used by all tests."""

    def __init__(self, test_db_path: str = ":memory:"):
        self._lock = threading.RLock()
        self._fernet = None

        database_url = "sqlite:///:memory:" if test_db_path == ":memory:" else f"sqlite:///{test_db_path}"
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        # Do NOT call clear_db() — avoids timezone issues with SQLite


@pytest.fixture
def db() -> Generator[SqliteDbClient, None, None]:
    """Fixture providing a clean in-memory database instance for testing."""
    db_instance = SqliteDbClient(":memory:")
    with db_instance.get_session() as session:
        session.execute(text("DELETE FROM appointment"))
        session.execute(text("DELETE FROM watch"))
        session.execute(text("DELETE FROM medicine"))
        session.commit()
    yield db_instance


@pytest.fixture
def db_client() -> Generator[SqliteDbClient, None, None]:
    """Fixture providing a clean DbClient instance with in-memory database for testing."""
    db_client_instance = SqliteDbClient(":memory:")
    with db_client_instance.get_session() as session:
        session.execute(text("DELETE FROM appointment"))
        session.execute(text("DELETE FROM watch"))
        session.execute(text("DELETE FROM medicine"))
        session.commit()
    yield db_client_instance


def test_clear_db(db: SqliteDbClient) -> None:
    """
    Test that clear_db method removes only past appointments.
    """
    now = datetime.datetime.now(pytz.timezone("Europe/Warsaw"))
    past_date = now - datetime.timedelta(days=1)
    future_date = now + datetime.timedelta(days=1)

    with db.get_session() as session:
        session.add(
            MedicoverAppointmentModel(
                clinic=1,
                doctor=11,
                date=past_date,
                specialty=23,
                visitType="Center",
                bookingString="booking1",
            )
        )
        session.add(
            MedicoverAppointmentModel(
                clinic=2,
                doctor=22,
                date=future_date,
                specialty=24,
                visitType="Center",
                bookingString="booking2",
            )
        )
        session.commit()

    db.clear_db()

    with db.get_session() as session:
        appointments = session.query(MedicoverAppointmentModel).all()
        assert len(appointments) == 1
        appointment_date = appointments[0].__dict__["date"]
        assert appointment_date >= now.replace(tzinfo=None)

    clinicId = 1
    doctorId = 2

    with db.get_session() as session:
        session.add(
            MedicoverAppointmentModel(
                clinic=clinicId,
                doctor=doctorId,
                date=datetime.datetime(2023, 10, 10, 10, 0, 0),
                specialty=3,
                visitType="visitType1",
                bookingString="bookingString1",
                bookingIdentifier=1,
            )
        )
        session.add(
            MedicoverAppointmentModel(
                clinic=11,
                doctor=22,
                date=datetime.datetime(2023, 10, 11, 10, 0, 0),
                specialty=33,
                visitType="visitType2",
                bookingString="bookingString2",
                bookingIdentifier=None,
            )
        )
        session.commit()

    booked_appointments = db.get_booked_appointments()
    assert len(booked_appointments) == 1
    assert booked_appointments[0][1].clinic.id == clinicId
    assert booked_appointments[0][1].doctor.id == doctorId


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

    with db.get_session() as session:
        session.add(
            MedicoverAppointmentModel(
                clinic=clinic.id,
                doctor=doctor.id,
                date=date_time,
                specialty=specialty.id,
                visitType="visitType1",
                bookingString="bookingString1",
                bookingIdentifier=0,
            )
        )
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
    with db.get_session() as session:
        session.add(
            MedicoverAppointmentModel(
                clinic=111,
                doctor=222,
                date=datetime.datetime(2023, 10, 10, 10, 0, 0),
                specialty=333,
                visitType="visitType1",
                bookingString="bookingString1",
                bookingIdentifier=1,
            )
        )
        session.commit()

    with db.get_session() as session:
        appointment_id = session.query(MedicoverAppointmentModel).first().id

    db.remove_appointment(appointment_id)

    with db.get_session() as session:
        appointments = session.query(MedicoverAppointmentModel).filter_by(id=appointment_id).all()
        assert len(appointments) == 0


def test_save_watch_with_not_all_fields(db):
    region = 200
    specialty = 9
    watch = Watch(
        id=0,
        region=IdValue(region),
        city="uuu",
        specialty=[IdValue(specialty)],
        clinic=IdValue(1337),
        doctor=IdValue(2137),
        start_date=datetime.date.fromisoformat("2023-10-10"),
        end_date=datetime.date.fromisoformat("2023-10-11"),
        time_range=WatchTimeRange("09:00:00-17:00:00"),
        auto_book=True,
    )

    db.save_watch(watch)

    with db.get_session() as session:
        watches = session.query(MedicoverWatchModel).filter_by(region=region, specialty=str(specialty)).all()
        assert len(watches) == 1
        assert watches[0].region == region
        assert watches[0].specialty == str(specialty)


def test_remove_watch(db):
    with db.get_session() as session:
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
        session.add(watch_model)
        session.commit()
        watch_id = watch_model.id

    assert db.remove_watch(watch_id)

    with db.get_session() as session:
        watches = session.query(MedicoverWatchModel).filter_by(id=watch_id).all()
        assert len(watches) == 0


def test_get_watches(db):
    with db.get_session() as session:
        session.add(
            MedicoverWatchModel(
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
        )
        session.add(
            MedicoverWatchModel(
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
        )
        session.commit()

    watches = db.get_watches()
    assert len(watches) == 2
    assert watches[0].region.id == 1
    assert watches[1].region.id == 11
    assert flatten_exclusions(watches[0].exclusions) == "doctor:123;clinic:456"
    assert watches[1].exclusions is None
    assert watches[0].type == "Standard"
    assert watches[1].type == "DiagnosticProcedure"


def test_dbclient_get_watches(db_client):
    with db_client.get_session() as session:
        session.add(
            MedicoverWatchModel(
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
        )
        session.add(
            MedicoverWatchModel(
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
        )
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
    with db_client.get_session() as session:
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
        session.add(watch_model)
        session.commit()
        watch_id = watch_model.id

    assert db_client.remove_watch(watch_id)

    with db_client.get_session() as session:
        watches = session.query(MedicoverWatchModel).filter_by(id=watch_id).all()
        assert len(watches) == 0


def test_dbclient_save_watch(db_client):
    region = 200
    specialty = 9
    watch = Watch(
        id=0,
        region=IdValue(region),
        city="Aszchabad",
        specialty=[IdValue(specialty)],
        clinic=IdValue(1337),
        doctor=IdValue(2137),
        start_date=datetime.date.fromisoformat("2023-10-10"),
        end_date=datetime.date.fromisoformat("2023-10-11"),
        time_range=WatchTimeRange("09:00:00-17:00:00"),
        auto_book=True,
        exclusions=parse_exclusions("doctor:123,456;clinic:789,1011"),
        type=WatchType.EXAMINATION,
    )

    db_client.save_watch(watch)

    with db_client.get_session() as session:
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
    watch = Watch(
        id=0,
        region=IdValue(region),
        city="Aszchabad",
        specialty=[IdValue(s) for s in specialty],
        clinic=IdValue(1337),
        doctor=IdValue(2137),
        start_date=datetime.date.fromisoformat("2023-10-10"),
        end_date=datetime.date.fromisoformat("2023-10-11"),
        time_range=WatchTimeRange("09:00:00-17:00:00"),
        auto_book=True,
        type=WatchType.EXAMINATION,
    )

    db_client.save_watch(watch)
    specialty_str = ",".join([str(s) for s in specialty])

    with db_client.get_session() as session:
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

    with db_client.get_session() as session:
        session.add(
            MedicoverAppointmentModel(
                clinic=clinic.id,
                doctor=doctor.id,
                date=date_time,
                specialty=specialty.id,
                visitType="visitType1",
                bookingString="bookingString1",
                bookingIdentifier=None,
            )
        )
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

    with db_client.get_session() as session:
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

    with db_client.get_session() as session:
        appointments = session.query(MedicoverAppointmentModel).filter_by(clinic=clinic.id, doctor=doctor.id).all()
        assert len(appointments) == 2
        assert appointments[0].clinic == clinic.id
        assert appointments[0].doctor == doctor.id
        assert appointments[1].clinic == clinic.id
        assert appointments[1].doctor == doctor.id


def test_dbclient_save_appointments_filters_existing(db_client):
    """Appointments already in the DB must be filtered out, new ones inserted."""
    clinic = IdValue(10, "c")
    doctor = IdValue(20, "d")
    specialty = IdValue(30, "s")

    existing = Appointment.initialize(
        clinic=clinic,
        doctor=doctor,
        date_time="2024-01-01 09:00:00",
        specialty=specialty,
        visit_type="v",
        booking_string="b",
    )
    new_ap = Appointment.initialize(
        clinic=clinic,
        doctor=doctor,
        date_time="2024-01-02 09:00:00",
        specialty=specialty,
        visit_type="v",
        booking_string="b",
    )

    db_client.add_appointment_history(existing)

    result = db_client.save_appointments_and_filter_old([existing, new_ap])

    assert len(result) == 1
    assert result[0].date_time == new_ap.date_time

    with db_client.get_session() as session:
        rows = session.query(MedicoverAppointmentModel).filter_by(clinic=clinic.id, doctor=doctor.id).all()
        assert len(rows) == 2


def test_dbclient_save_appointments_all_existing(db_client):
    """When all appointments already exist, nothing is inserted and an empty list is returned."""
    clinic = IdValue(11, "c")
    doctor = IdValue(21, "d")
    specialty = IdValue(31, "s")

    ap = Appointment.initialize(
        clinic=clinic,
        doctor=doctor,
        date_time="2024-03-01 08:00:00",
        specialty=specialty,
        visit_type="v",
        booking_string="b",
    )
    db_client.add_appointment_history(ap)

    result = db_client.save_appointments_and_filter_old([ap])

    assert result == []

    with db_client.get_session() as session:
        rows = session.query(MedicoverAppointmentModel).filter_by(clinic=clinic.id, doctor=doctor.id).all()
        assert len(rows) == 1


def test_get_existing_appointment_keys_empty_input(db_client):
    """Empty input returns an empty set without hitting the DB."""
    keys = db_client.get_existing_appointment_keys([])
    assert keys == set()


def test_get_existing_appointment_keys_bulk(db_client):
    """Returns keys only for appointments that actually exist."""
    clinic = IdValue(50, "c")
    doctor = IdValue(60, "d")
    specialty = IdValue(70, "s")

    ap1 = Appointment.initialize(
        clinic=clinic,
        doctor=doctor,
        date_time="2024-06-01 10:00:00",
        specialty=specialty,
        visit_type="v",
        booking_string="b",
    )
    ap2 = Appointment.initialize(
        clinic=clinic,
        doctor=doctor,
        date_time="2024-06-02 10:00:00",
        specialty=specialty,
        visit_type="v",
        booking_string="b",
    )
    ap3 = Appointment.initialize(
        clinic=clinic,
        doctor=doctor,
        date_time="2024-06-03 10:00:00",
        specialty=specialty,
        visit_type="v",
        booking_string="b",
    )
    db_client.add_appointment_history(ap1)
    db_client.add_appointment_history(ap3)

    keys = db_client.get_existing_appointment_keys([ap1, ap2, ap3])

    assert len(keys) == 2
    assert (ap1.clinic.id, ap1.doctor.id, ap1.date_time) in keys
    assert (ap3.clinic.id, ap3.doctor.id, ap3.date_time) in keys
    assert (ap2.clinic.id, ap2.doctor.id, ap2.date_time) not in keys


def test_dbclient_list_booked_appointments(db_client):
    with db_client.get_session() as session:
        session.add(
            MedicoverAppointmentModel(
                clinic=234,
                doctor=345,
                date=datetime.datetime(2025, 4, 10, 10, 0, 0),
                specialty=456,
                visitType="visitType1",
                bookingString="bookingString1",
                bookingIdentifier=123123123,
            )
        )
        session.add(
            MedicoverAppointmentModel(
                clinic=4,
                doctor=3,
                date=datetime.datetime(2025, 4, 10, 10, 0, 0),
                specialty=2,
                visitType="visitType1",
                bookingString="bookingString2",
                bookingIdentifier=1,
            )
        )
        session.add(
            MedicoverAppointmentModel(
                clinic=111,
                doctor=222,
                date=datetime.datetime(2025, 4, 10, 10, 0, 0),
                specialty=333,
                visitType="visitType1",
                bookingString="bookingString3",
                bookingIdentifier=None,
            )
        )
        session.commit()

    booked_aps = db_client.get_booked_appointments()
    assert len(booked_aps) == 2


def test_edit_watch_updates_fields(db_client):
    region = 1
    specialty = [9]
    watch = Watch(
        id=0,
        region=IdValue(region),
        city="OldCity",
        specialty=[IdValue(s) for s in specialty],
        clinic=IdValue(1337),
        doctor=IdValue(2137),
        start_date=datetime.date.fromisoformat("2023-10-10"),
        end_date=datetime.date.fromisoformat("2023-10-11"),
        time_range=WatchTimeRange("09:00:00-17:00:00"),
        auto_book=False,
    )
    db_client.save_watch(watch)

    with db_client.get_session() as session:
        watch_record = session.query(MedicoverWatchModel).filter_by(region=region, city="OldCity").first()
        watch_id = watch_record.id

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

    with db_client.get_session() as session:
        updated = session.query(MedicoverWatchModel).filter_by(id=watch_id).first()
        assert updated.city == "NewCity"
        assert updated.clinic == 2024
        assert updated.startDate == datetime.date(2024, 1, 1)
        assert updated.endDate == datetime.date(2024, 12, 31)
        assert updated.timeRange == "08:00:00-16:00:00"
        assert updated.autobook is True
        assert updated.exclusions == "doctor:123;clinic:456"


def test_edit_watch_no_fields_to_update(db_client):
    region = 2
    specialty = [10]
    watch = Watch(
        id=0,
        region=IdValue(region),
        city="City",
        specialty=[IdValue(s) for s in specialty],
        clinic=IdValue(555),
        doctor=IdValue(666),
        start_date=datetime.date.fromisoformat("2023-10-10"),
        end_date=datetime.date.fromisoformat("2023-10-11"),
        time_range=WatchTimeRange("09:00:00-17:00:00"),
        auto_book=False,
    )
    db_client.save_watch(watch)

    with db_client.get_session() as session:
        watch_record = session.query(MedicoverWatchModel).filter_by(region=region, city="City").first()
        watch_id = watch_record.id

    db_client.update_watch(watch_id)

    with db_client.get_session() as session:
        updated = session.query(MedicoverWatchModel).filter_by(id=watch_id).first()
        assert updated.city == "City"
        assert updated.clinic == 555
