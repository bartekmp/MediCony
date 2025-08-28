"""
Medicover-specific database logic using SQLAlchemy for PostgreSQL.
"""

import datetime
from typing import List, Optional, Tuple

from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError

from src.database.base_db import BaseDbLogic
from src.logger import log
from src.medicover.appointment import Appointment as MedicoverAppointment
from src.medicover.watch import Watch as MedicoverWatch
from src.medicover.watch import flatten_exclusions
from src.models import MedicoverAppointmentModel, MedicoverWatchModel


class MedicoverDbLogic(BaseDbLogic):
    def __init__(self):
        super().__init__()
        self.clear_db()

    def clear_db(self):
        """Clear old appointments and watches."""
        now = datetime.datetime.now()
        today = datetime.date.today()

        with self._lock:
            try:
                with self.get_session() as session:
                    # Delete appointments older than the current time
                    session.query(MedicoverAppointmentModel).filter(MedicoverAppointmentModel.date < now).delete()
                    # Delete watches that have ended
                    session.query(MedicoverWatchModel).filter(
                        and_(MedicoverWatchModel.endDate.isnot(None), MedicoverWatchModel.endDate < today)
                    ).delete()
                    session.commit()
                    log.info("Database cleared of old appointments and ended watches")
            except SQLAlchemyError as e:
                log.error(f"Error clearing database: {e}")
                raise

    def appointment_exists(self, appointment: MedicoverAppointment) -> bool:
        """Check if an appointment already exists in the database."""
        with self._lock:
            try:
                with self.get_session() as session:
                    result = (
                        session.query(MedicoverAppointmentModel)
                        .filter(
                            and_(
                                MedicoverAppointmentModel.clinic == appointment.clinic.id,
                                MedicoverAppointmentModel.doctor == appointment.doctor.id,
                                MedicoverAppointmentModel.date == appointment.date_time,
                            )
                        )
                        .first()
                    )
                    return result is not None
            except SQLAlchemyError as e:
                log.error(f"Error checking appointment existence: {e}")
                return False

    def get_booked_appointments(self) -> List[Tuple]:
        """Fetch all appointments that have a booking identifier."""
        with self._lock:
            try:
                with self.get_session() as session:
                    appointments = (
                        session.query(MedicoverAppointmentModel)
                        .filter(MedicoverAppointmentModel.bookingIdentifier.isnot(None))
                        .all()
                    )
                    # Convert to tuples for compatibility
                    return [
                        (
                            app.id,
                            app.clinic,
                            app.doctor,
                            app.date,
                            app.specialty,
                            app.visitType,
                            app.bookingString,
                            app.bookingIdentifier,
                            app.account,
                        )
                        for app in appointments
                    ]
            except SQLAlchemyError as e:
                log.error(f"Error getting booked appointments: {e}")
                return []

    def add_appointment_history(self, appointment: MedicoverAppointment):
        """Add an appointment to the database."""
        with self._lock:
            try:
                with self.get_session() as session:
                    new_appointment = MedicoverAppointmentModel(
                        clinic=appointment.clinic.id,
                        doctor=appointment.doctor.id,
                        date=appointment.date_time,
                        specialty=appointment.specialty.id,
                        visitType=appointment.visit_type,
                        bookingString=appointment.booking_string,
                        account=appointment.account,
                    )
                    session.add(new_appointment)
                    session.commit()
            except SQLAlchemyError as e:
                log.error(f"Error adding appointment: {e}")
                raise

    def update_appointment(self, appointment: MedicoverAppointment):
        """Update an existing appointment in the database."""
        with self._lock:
            try:
                with self.get_session() as session:
                    existing = (
                        session.query(MedicoverAppointmentModel)
                        .filter(
                            and_(
                                MedicoverAppointmentModel.clinic == appointment.clinic.id,
                                MedicoverAppointmentModel.doctor == appointment.doctor.id,
                                MedicoverAppointmentModel.date == appointment.date_time,
                            )
                        )
                        .first()
                    )

                    if existing:
                        # Update using session.merge or direct attribute setting
                        session.query(MedicoverAppointmentModel).filter_by(id=existing.id).update(
                            {
                                "specialty": appointment.specialty.id,
                                "visitType": appointment.visit_type,
                                "bookingString": appointment.booking_string,
                                "bookingIdentifier": getattr(appointment, "booking_identifier", None),
                                "account": getattr(appointment, "account", None),
                            }
                        )
                        session.commit()
            except SQLAlchemyError as e:
                log.error(f"Error updating appointment: {e}")
                raise

    def remove_appointment(self, appointment_id: int) -> bool:
        """Remove an appointment from the database by ID."""
        with self._lock:
            try:
                with self.get_session() as session:
                    deleted_count = session.query(MedicoverAppointmentModel).filter_by(id=appointment_id).delete()
                    session.commit()
                    return deleted_count > 0
            except SQLAlchemyError as e:
                log.error(f"Error removing appointment: {e}")
                raise

    def save_watch(self, watch: MedicoverWatch) -> int:
        """Save a watch to the database and return its ID."""
        with self._lock:
            try:
                with self.get_session() as session:
                    specialties_str = ",".join(map(str, [s.id for s in watch.specialty]))
                    new_watch = MedicoverWatchModel(
                        region=watch.region.id,
                        city=watch.city,
                        specialty=specialties_str,
                        clinic=watch.clinic.id if watch.clinic else None,
                        doctor=watch.doctor.id if watch.doctor else None,
                        startDate=watch.start_date if watch.start_date else None,
                        endDate=watch.end_date if watch.end_date else None,
                        timeRange=str(watch.time_range) if watch.time_range else None,
                        autobook=watch.auto_book,
                        exclusions=flatten_exclusions(watch.exclusions) if watch.exclusions else None,
                        type=str(watch.type.value) if watch.type else None,
                        account=watch.account,
                    )
                    session.add(new_watch)
                    session.commit()
                    session.refresh(new_watch)
                    return new_watch.id  # type: ignore
            except SQLAlchemyError as e:
                log.error(f"Error saving watch: {e}")
                raise

    def get_watch(self, watch_id: int) -> Optional[Tuple]:
        """Get a watch by ID."""
        with self._lock:
            try:
                with self.get_session() as session:
                    watch = session.query(MedicoverWatchModel).filter(MedicoverWatchModel.id == watch_id).first()
                    if watch:
                        return (
                            watch.id,
                            watch.region,
                            watch.city,
                            watch.specialty,
                            watch.clinic,
                            watch.doctor,
                            watch.startDate,
                            watch.endDate,
                            watch.timeRange,
                            watch.autobook,
                            watch.exclusions,
                            watch.type,
                            watch.account,
                        )
                    return None
            except SQLAlchemyError as e:
                log.error(f"Error getting watch: {e}")
                return None

    def get_watches(self) -> List[Tuple]:
        """Get all watches."""
        with self._lock:
            try:
                with self.get_session() as session:
                    watches = session.query(MedicoverWatchModel).all()
                    return [
                        (
                            w.id,
                            w.region,
                            w.city,
                            w.specialty,
                            w.clinic,
                            w.doctor,
                            w.startDate,
                            w.endDate,
                            w.timeRange,
                            w.autobook,
                            w.exclusions,
                            w.type,
                            w.account,
                        )
                        for w in watches
                    ]
            except SQLAlchemyError as e:
                log.error(f"Error getting watches: {e}")
                return []

    def remove_watch(self, watch_id: int) -> bool:
        """Remove a watch from the database."""
        with self._lock:
            try:
                with self.get_session() as session:
                    result = session.query(MedicoverWatchModel).filter(MedicoverWatchModel.id == watch_id).delete()
                    session.commit()
                    return result > 0
            except SQLAlchemyError as e:
                log.error(f"Error removing watch: {e}")
                return False

    def update_watch(
        self,
        watch_id: int,
        city: Optional[str] = None,
        clinic_id: Optional[int] = None,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None,
        time_range: Optional[str] = None,
        exclusions: Optional[str] = None,
        auto_book: Optional[bool] = None,
        account: Optional[str] = None,
    ) -> bool:
        """Update a watch in the database."""
        with self._lock:
            try:
                with self.get_session() as session:
                    watch = session.query(MedicoverWatchModel).filter(MedicoverWatchModel.id == watch_id).first()
                    if not watch:
                        return False

                    # Build update dictionary for non-None values
                    update_data = {}
                    if city is not None:
                        update_data["city"] = city
                    if clinic_id is not None:
                        update_data["clinic"] = clinic_id
                    if start_date is not None:
                        update_data["startDate"] = start_date
                    if end_date is not None:
                        update_data["endDate"] = end_date
                    if time_range is not None:
                        update_data["timeRange"] = time_range
                    if exclusions is not None:
                        update_data["exclusions"] = exclusions
                    if auto_book is not None:
                        update_data["autobook"] = auto_book
                    if account is not None:
                        update_data["account"] = account

                    # Perform the update using the proper SQLAlchemy method
                    if update_data:
                        session.query(MedicoverWatchModel).filter_by(id=watch_id).update(update_data)

                    session.commit()
                    return True
            except SQLAlchemyError as e:
                log.error(f"Error updating watch: {e}")
                return False
