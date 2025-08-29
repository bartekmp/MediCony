"""Tests for multi-account features (watch and appointment account alias persistence).

These tests focus on the new "account" column additions to watch and appointment tables
and related behaviors in service/database layers.
"""

import pytest
from sqlalchemy import text

from src.medicover.watch import Watch, WatchType
from src.medicover.appointment import Appointment
from src.id_value_util import IdValue
from src.medicover.services.watch_service import WatchService

# Reuse SQLite-based testing logic by subclassing to avoid side-effects
from tests.test_db import SqliteDbLogic, SqliteDbClient  # type: ignore


class DummyAPI:
    async def update_watch_metadata(self, watch):
        return


@pytest.fixture
def db_logic():
    return SqliteDbLogic(":memory:")


@pytest.fixture
def db_client():
    return SqliteDbClient(":memory:")


@pytest.fixture
def watch_service(db_client):
    return WatchService(api_client=DummyAPI(), db_client=db_client)  # type: ignore


def test_watch_persists_account_alias(db_client):
    # Create a watch with an explicit account alias
    watch = Watch.from_tuple(
        (
            0,  # id (ignored on save)
            101,  # region id
            "CityX",  # city
            [9],  # specialties
            None,  # clinic
            None,  # doctor
            "2025-01-01",  # start
            "2025-12-31",  # end
            "00:00:00-*",  # time range
            False,  # autobook
            None,  # exclusions
            WatchType.STANDARD.value,  # type
            "accA",  # account alias
        )
    )
    new_id = db_client.save_watch(watch)
    # Fetch back via client (which normalizes)
    stored = db_client.get_watch(new_id)
    assert stored is not None
    assert stored.account == "accA"


def test_watch_service_default_account_on_update(db_client, watch_service):
    # Create watch without account alias
    watch = Watch.from_tuple(
        (
            0,
            102,
            "CityY",
            [10],
            None,
            None,
            "2025-01-01",
            "2025-12-31",
            "00:00:00-*",
            False,
            None,
            WatchType.STANDARD.value,
        )
    )
    watch_id = db_client.save_watch(watch)
    existing = db_client.get_watch(watch_id)
    assert existing is not None
    assert existing.account is None  # initially not set
    # Use service update (injects default account if missing)
    watch_service.update_watch(existing, city="CityY2")
    updated = db_client.get_watch(watch_id)
    assert updated is not None
    assert updated.account == "default"


def test_appointment_history_with_account(db_logic):
    clinic = IdValue(1, "Clinic")
    doctor = IdValue(2, "Doctor")
    specialty = IdValue(3, "Spec")
    ap = Appointment.initialize(
        clinic=clinic,
        doctor=doctor,
        date_time="2025-02-02 10:00:00",
        specialty=specialty,
        visit_type="Center",
        booking_string="bs1",
        booking_identifier=123,
        account="accB",
    )
    db_logic.add_appointment_history(ap)
    with db_logic.get_session() as session:
        row = session.execute(
            text("SELECT clinic, doctor, specialty, bookingstring, bookingidentifier, account FROM appointment")
        ).fetchone()
        assert row is not None
        assert row[5] == "accB"


def test_update_appointment_sets_account(db_logic):
    clinic = IdValue(10, "Clinic2")
    doctor = IdValue(20, "Doctor2")
    specialty = IdValue(30, "Spec2")
    # First add without account
    ap_initial = Appointment.initialize(
        clinic=clinic,
        doctor=doctor,
        date_time="2025-03-03 11:00:00",
        specialty=specialty,
        visit_type="Center",
        booking_string="bs2",
        booking_identifier=None,
    )
    db_logic.add_appointment_history(ap_initial)
    # Now update with booking identifier & account
    ap_initial.booking_identifier = 777
    ap_initial.account = "accC"
    db_logic.update_appointment(ap_initial)
    with db_logic.get_session() as session:
        row = session.execute(
            text("SELECT bookingidentifier, account FROM appointment WHERE clinic=10 AND doctor=20")
        ).fetchone()
        assert row is not None
        assert str(row[0]) == "777"
        assert row[1] == "accC"
