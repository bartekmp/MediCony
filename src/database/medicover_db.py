"""
Medicover database client.
"""

import datetime
from typing import List, Optional, Tuple

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import and_, or_
from sqlalchemy.exc import SQLAlchemyError

from src.config import get_config
from src.database.base_db import BaseDbLogic
from src.id_value_util import IdValue
from src.logger import log
from src.medicover.appointment import Appointment as MedicoverAppointment
from src.medicover.watch import Watch as MedicoverWatch
from src.medicover.watch import WatchTimeRange, WatchType, flatten_exclusions, parse_exclusions
from src.models import (
    MedicoverAccountSessionModel,
    MedicoverAppointmentModel,
    MedicoverWatchModel,
)


class MedicoverDbClient(BaseDbLogic):
    def __init__(self):
        super().__init__("Medicover")

        self._fernet = None
        encryption_key = get_config().encryption_key
        if encryption_key:
            try:
                self._fernet = Fernet(encryption_key.encode("utf-8"))
            except Exception as e:
                log.error(f"Invalid MEDICONY_ENCRYPTION_KEY provided: {e}")

        self.clear_db()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _row_to_watch(self, row: MedicoverWatchModel) -> MedicoverWatch:
        return MedicoverWatch(
            id=row.id,
            region=IdValue(row.region),
            city=row.city,
            specialty=[IdValue(int(s)) for s in row.specialty.split(",")],
            clinic=IdValue(row.clinic) if row.clinic is not None else None,
            doctor=IdValue(row.doctor) if row.doctor is not None else None,
            start_date=row.startDate,
            end_date=row.endDate,
            time_range=WatchTimeRange(row.timeRange) if row.timeRange else WatchTimeRange.default(),
            auto_book=bool(row.autobook),
            exclusions=parse_exclusions(row.exclusions),
            type=WatchType(row.type) if row.type else WatchType.STANDARD,
            account=row.account,
        )

    def _row_to_appointment(self, row: MedicoverAppointmentModel) -> MedicoverAppointment:
        return MedicoverAppointment.initialize(
            clinic=IdValue(row.clinic),
            doctor=IdValue(row.doctor),
            date_time=row.date.isoformat(),
            specialty=IdValue(row.specialty),
            visit_type=row.visitType,
            booking_string=row.bookingString,
            booking_identifier=row.bookingIdentifier,
            account=row.account,
        )

    # ------------------------------------------------------------------
    # Housekeeping
    # ------------------------------------------------------------------

    def clear_db(self):
        """Clear old appointments and expired watches."""
        now = datetime.datetime.now()
        today = datetime.date.today()

        with self._lock:
            try:
                with self.get_session() as session:
                    session.query(MedicoverAppointmentModel).filter(MedicoverAppointmentModel.date < now).delete()
                    session.query(MedicoverWatchModel).filter(
                        and_(
                            MedicoverWatchModel.endDate.isnot(None),
                            MedicoverWatchModel.endDate < today,
                        )
                    ).delete()
                    session.commit()
                    log.info("Database cleared of old appointments and ended watches")
            except SQLAlchemyError as e:
                log.error(f"Error clearing database: {e}")
                raise

    # ------------------------------------------------------------------
    # Watch operations
    # ------------------------------------------------------------------

    def get_watch(self, watch_id: int) -> Optional[MedicoverWatch]:
        with self._lock:
            try:
                with self.get_session() as session:
                    row = session.query(MedicoverWatchModel).filter(MedicoverWatchModel.id == watch_id).first()
                    return self._row_to_watch(row) if row else None
            except SQLAlchemyError as e:
                log.error(f"Error getting watch: {e}")
                return None

    def get_watches(self) -> List[MedicoverWatch]:
        with self._lock:
            try:
                with self.get_session() as session:
                    return [self._row_to_watch(row) for row in session.query(MedicoverWatchModel).all()]
            except SQLAlchemyError as e:
                log.error(f"Error getting watches: {e}")
                return []

    def save_watch(self, watch: MedicoverWatch) -> int:
        with self._lock:
            try:
                with self.get_session() as session:
                    new_watch = MedicoverWatchModel(
                        region=watch.region.id,
                        city=watch.city,
                        specialty=",".join(str(s.id) for s in watch.specialty),
                        clinic=watch.clinic.id if watch.clinic else None,
                        doctor=watch.doctor.id if watch.doctor else None,
                        startDate=watch.start_date or None,
                        endDate=watch.end_date or None,
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
        with self._lock:
            try:
                with self.get_session() as session:
                    watch = session.query(MedicoverWatchModel).filter(MedicoverWatchModel.id == watch_id).first()
                    if not watch:
                        return False

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

                    if update_data:
                        session.query(MedicoverWatchModel).filter_by(id=watch_id).update(update_data)
                    session.commit()
                    return True
            except SQLAlchemyError as e:
                log.error(f"Error updating watch: {e}")
                return False

    def remove_watch(self, watch_id: int) -> bool:
        with self._lock:
            try:
                with self.get_session() as session:
                    result = session.query(MedicoverWatchModel).filter(MedicoverWatchModel.id == watch_id).delete()
                    session.commit()
                    return result > 0
            except SQLAlchemyError as e:
                log.error(f"Error removing watch: {e}")
                return False

    # ------------------------------------------------------------------
    # Appointment operations
    # ------------------------------------------------------------------

    def add_appointment_history(self, appointment: MedicoverAppointment):
        with self._lock:
            try:
                with self.get_session() as session:
                    session.add(MedicoverAppointmentModel(
                        clinic=appointment.clinic.id,
                        doctor=appointment.doctor.id,
                        date=appointment.date_time,
                        specialty=appointment.specialty.id,
                        visitType=appointment.visit_type,
                        bookingString=appointment.booking_string,
                        account=appointment.account,
                    ))
                    session.commit()
            except SQLAlchemyError as e:
                log.error(f"Error adding appointment: {e}")
                raise

    def add_appointment_histories(self, appointments: List[MedicoverAppointment]):
        if not appointments:
            return
        with self._lock:
            try:
                with self.get_session() as session:
                    for appointment in appointments:
                        session.add(MedicoverAppointmentModel(
                            clinic=appointment.clinic.id,
                            doctor=appointment.doctor.id,
                            date=appointment.date_time,
                            specialty=appointment.specialty.id,
                            visitType=appointment.visit_type,
                            bookingString=appointment.booking_string,
                            account=appointment.account,
                        ))
                    session.commit()
            except SQLAlchemyError as e:
                log.error(f"Error adding multiple appointments: {e}")
                raise

    def update_appointment(self, appointment: MedicoverAppointment):
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
                        session.query(MedicoverAppointmentModel).filter_by(id=existing.id).update({
                            "specialty": appointment.specialty.id,
                            "visitType": appointment.visit_type,
                            "bookingString": appointment.booking_string,
                            "bookingIdentifier": getattr(appointment, "booking_identifier", None),
                            "account": getattr(appointment, "account", None),
                        })
                        session.commit()
            except SQLAlchemyError as e:
                log.error(f"Error updating appointment: {e}")
                raise

    def remove_appointment(self, appointment_id: int) -> bool:
        with self._lock:
            try:
                with self.get_session() as session:
                    deleted = session.query(MedicoverAppointmentModel).filter_by(id=appointment_id).delete()
                    session.commit()
                    return deleted > 0
            except SQLAlchemyError as e:
                log.error(f"Error removing appointment: {e}")
                raise

    def appointment_exists(self, appointment: MedicoverAppointment) -> bool:
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

    def get_existing_appointment_keys(self, appointments: List[MedicoverAppointment]) -> set:
        if not appointments:
            return set()
        with self._lock:
            try:
                with self.get_session() as session:
                    conditions = [
                        and_(
                            MedicoverAppointmentModel.clinic == a.clinic.id,
                            MedicoverAppointmentModel.doctor == a.doctor.id,
                            MedicoverAppointmentModel.date == a.date_time,
                        )
                        for a in appointments
                    ]
                    rows = (
                        session.query(
                            MedicoverAppointmentModel.clinic,
                            MedicoverAppointmentModel.doctor,
                            MedicoverAppointmentModel.date,
                        )
                        .filter(or_(*conditions))
                        .all()
                    )
                    return {(r.clinic, r.doctor, r.date) for r in rows}
            except SQLAlchemyError as e:
                log.error(f"Error fetching existing appointment keys: {e}")
                return set()

    def get_booked_appointments(self) -> List[Tuple[int, MedicoverAppointment]]:
        with self._lock:
            try:
                with self.get_session() as session:
                    rows = (
                        session.query(MedicoverAppointmentModel)
                        .filter(MedicoverAppointmentModel.bookingIdentifier.isnot(None))
                        .all()
                    )
                    return [(row.id, self._row_to_appointment(row)) for row in rows]
            except SQLAlchemyError as e:
                log.error(f"Error getting booked appointments: {e}")
                return []

    def save_appointments_and_filter_old(
        self, appointments: List[MedicoverAppointment]
    ) -> List[MedicoverAppointment]:
        existing_keys = self.get_existing_appointment_keys(appointments)
        new_appointments = [a for a in appointments if (a.clinic.id, a.doctor.id, a.date_time) not in existing_keys]
        if new_appointments:
            self.add_appointment_histories(new_appointments)
        return new_appointments

    # ------------------------------------------------------------------
    # Session (auth token) operations
    # ------------------------------------------------------------------

    def get_account_session(self, account: str) -> Optional[Tuple[str, str]]:
        with self._lock:
            try:
                with self.get_session() as session:
                    res = (
                        session.query(MedicoverAccountSessionModel)
                        .filter(MedicoverAccountSessionModel.account == account)
                        .first()
                    )
                    if res and res.deviceId and res.refreshToken:
                        refresh_token = res.refreshToken
                        if self._fernet:
                            try:
                                refresh_token = self._fernet.decrypt(refresh_token.encode("utf-8")).decode("utf-8")
                            except InvalidToken:
                                log.error(
                                    "Failed to decrypt the refresh token! The configured MEDICONY_ENCRYPTION_KEY "
                                    "doesn't match the one used to encrypt it, or the token was stored as "
                                    "plain-text before the key was added. Deleting invalid session..."
                                )
                                session.delete(res)
                                session.commit()
                                return None
                            except Exception as e:
                                log.error(f"Failed to decrypt the refresh token: {e}")
                                return None
                        return (res.deviceId, refresh_token)
                    return None
            except SQLAlchemyError as e:
                log.error(f"Error getting account session: {e}")
                return None

    def save_account_session(self, account: str, device_id: str, refresh_token: str):
        with self._lock:
            try:
                stored_refresh_token = refresh_token
                if self._fernet:
                    stored_refresh_token = self._fernet.encrypt(refresh_token.encode("utf-8")).decode("utf-8")

                with self.get_session() as session:
                    existing = (
                        session.query(MedicoverAccountSessionModel)
                        .filter(MedicoverAccountSessionModel.account == account)
                        .first()
                    )
                    if existing:
                        existing.deviceId = device_id
                        existing.refreshToken = stored_refresh_token
                    else:
                        session.add(MedicoverAccountSessionModel(
                            account=account,
                            deviceId=device_id,
                            refreshToken=stored_refresh_token,
                        ))
                    session.commit()
            except SQLAlchemyError as e:
                log.error(f"Error saving account session: {e}")
                raise
