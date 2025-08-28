"""
Medicover database client.
"""

import datetime
from typing import List, Optional, Tuple

from src.database.medicover_db import MedicoverDbLogic
from src.medicover.appointment import Appointment as MedicoverAppointment
from src.medicover.watch import Watch as MedicoverWatch


class MedicoverDbClient:
    def __init__(self):
        self.db = MedicoverDbLogic()

    def _parse_row_to_watch(self, row: Tuple) -> MedicoverWatch:
        # Convert a database row to a Watch object
        # Handle the case where multiple specialties are stored as a comma-separated string
        specialties = [int(w) for w in row[3].split(",")]
        # Row layout:
        # (id, region, city, [specialty_ids], clinic, doctor, startDate, endDate, timeRange,
        #  autobook, exclusions, type, account)
        watch_tuple = (
            row[0],
            row[1],
            row[2],
            specialties,
            row[4],
            row[5],
            row[6],
            row[7],
            row[8],
            row[9],
            row[10],
            row[11],
            row[12] if len(row) > 12 else None,
        )
        return MedicoverWatch.from_tuple(watch_tuple)

    def get_watch(self, watch_id: int) -> Optional[MedicoverWatch]:
        row = self.db.get_watch(watch_id)
        if row is None:
            return None
        return self._parse_row_to_watch(row)

    def get_watches(self) -> List[MedicoverWatch]:
        res = self.db.get_watches()
        watches = []
        for watch in res:
            watches.append(self._parse_row_to_watch(watch))
        return watches

    def remove_watch(self, watch_id: int) -> bool:
        return self.db.remove_watch(watch_id)

    def save_watch(self, watch: MedicoverWatch) -> int:
        return self.db.save_watch(watch)

    def update_appointment(self, appointment: MedicoverAppointment):
        if not self.db.appointment_exists(appointment):
            self.db.add_appointment_history(appointment)
        else:
            self.db.update_appointment(appointment)

    def save_appointments_and_filter_old(self, appointments: List[MedicoverAppointment]) -> List[MedicoverAppointment]:
        new_appointments = []
        for appointment in appointments:
            # Check if appointment in the local database
            if not self.db.appointment_exists(appointment):
                # If not, append it to the return list and add it to the local database
                new_appointments.append(appointment)
                self.db.add_appointment_history(appointment)

        return new_appointments

    def get_booked_appointments(self) -> List[Tuple[int, MedicoverAppointment]]:
        """Return list of (db_id, Appointment) for booked appointments."""
        appointments = self.db.get_booked_appointments()
        # Tuple layout: (id, clinic, doctor, date, specialty, visitType, bookingString, bookingIdentifier, account)
        result: List[Tuple[int, MedicoverAppointment]] = []
        for ap in appointments:
            result.append((ap[0], MedicoverAppointment.initialize_from_tuple(ap)))
        return result

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
        return self.db.update_watch(
            watch_id,
            city,
            clinic_id,
            start_date,
            end_date,
            time_range,
            exclusions,
            auto_book,
            account,
        )
