import datetime

from .appointment import Appointment
from .watch import WatchExclusions


def is_excluded(appointment: Appointment, exclusions: WatchExclusions) -> bool:
    if not exclusions:
        return False
    if "doctor" in exclusions and str(appointment.doctor.id) in exclusions["doctor"]:
        return True
    if "clinic" in exclusions and str(appointment.clinic.id) in exclusions["clinic"]:
        return True
    return False


def match_single_appointment_to_be_canceled(
    appointment_to_be_canceled: Appointment, server_ap_list: list
) -> str | None:
    for ap in server_ap_list:
        server_side_ap = Appointment(ap)
        if server_side_ap == appointment_to_be_canceled:
            return ap["id"]
    return None


def match_single_appointment(
    specialty: int,
    clinic: int | None,
    doctor: int | None,
    date_time: datetime.datetime,
    appointments: list[Appointment],
    exact_time_match: bool = True,
    exact_date_match: bool = True,
) -> Appointment | None:
    for appointment in appointments:
        if (
            appointment.specialty.id == specialty
            and (not clinic or appointment.clinic.id == clinic)
            and (not doctor or appointment.doctor.id == doctor)
            and (
                (not exact_time_match and not exact_date_match)
                or (exact_time_match and appointment.date_time == date_time)
                or (exact_date_match and appointment.date_time.date() == date_time.date())
            )
        ):
            return appointment
    return None


def match_within_date_range(
    specialty: int,
    clinic: int | None,
    doctor: int | None,
    start_date: datetime.date,
    end_date: datetime.date | None,
    appointments: list[Appointment],
) -> list[Appointment]:
    matching = []
    if not end_date:
        end_date = datetime.date.max
    for appointment in appointments:
        if (
            appointment.specialty.id == specialty
            and (not clinic or appointment.clinic.id == clinic)
            and (not doctor or appointment.doctor.id == doctor)
            and start_date <= appointment.date_time.date() <= end_date
        ):
            matching.append(appointment)
    return matching
