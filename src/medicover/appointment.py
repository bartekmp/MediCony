import datetime

from src.id_value_util import IdValue


class Appointment:
    clinic: IdValue
    date_time: datetime.datetime
    doctor: IdValue
    specialty: IdValue
    visit_type: str = "Center"
    booking_string: str | None = None
    booking_identifier: int | None = None
    database_row_id: int | None = None
    account: str | None = None  # Multi-account context

    def __init__(self, data: dict | None = None):
        if not data:
            return

        if "date" in data:
            data["appointmentDate"] = data["date"]

        self.clinic = IdValue(int(data["clinic"]["id"]), data["clinic"]["name"])
        self.date_time = datetime.datetime.fromisoformat(data["appointmentDate"])

        if data["doctor"] is None:
            self.doctor = IdValue(0, "Ambulatory additional visit")
        else:
            self.doctor = IdValue(int(data["doctor"]["id"]), data["doctor"]["name"])

        self.specialty = IdValue(int(data["specialty"]["id"]), data["specialty"]["name"])
        self.visit_type = data["visitType"]
        self.booking_string = data.get("bookingString", None)

    @staticmethod
    def initialize(
        clinic: IdValue,
        date_time: str,
        doctor: IdValue,
        specialty: IdValue,
        visit_type: str = "Center",
        booking_string: str | None = None,
        booking_identifier: int | None = None,
        account: str | None = None,
    ) -> "Appointment":
        ap = Appointment()
        ap.clinic = clinic
        ap.doctor = doctor
        ap.date_time = datetime.datetime.fromisoformat(date_time)
        ap.specialty = specialty
        ap.visit_type = visit_type
        ap.booking_string = booking_string
        ap.booking_identifier = booking_identifier
        ap.account = account
        return ap

    def __eq__(self, other) -> bool:
        return (
            self.clinic.id == other.clinic.id
            and self.doctor.id == other.doctor.id
            and self.date_time == other.date_time
            and self.specialty.id == other.specialty.id
            and self.visit_type == other.visit_type
        )

    def debug_str(self) -> str:
        lines = [
            f"Date: {self.date_time}",
            f"Clinic: {self.clinic.value} ({self.clinic.id})",
            f"Doctor: {self.doctor.value} ({self.doctor.id})",
            f"Specialty: {self.specialty.value} ({self.specialty.id})",
            f"Type: {self.visit_type}",
            f"Booked: {'No' if self.booking_identifier is None else 'Yes (ID: ' + str(self.booking_identifier) + ')'}",
            f"Account: {self.account if self.account else 'N/A'}",
        ]
        return "\n".join(lines)

    def __str__(self) -> str:
        lines = []
        if self.database_row_id:
            lines.append(f"ID: {self.database_row_id}")
        lines.extend([
            f"Date: {self.date_time}",
            f"Clinic: {self.clinic.value}",
            f"Doctor: {self.doctor.value}",
            f"Specialty: {self.specialty.value}",
            f"Type: {self.visit_type}",
            f"Booked: {'No' if self.booking_identifier is None else 'Yes (ID: ' + str(self.booking_identifier) + ')'}",
            f"Account: {self.account if self.account else 'N/A'}",
        ])
        return "\n".join(lines)

    def notification_str(self) -> list[str]:
        return self.__str__().splitlines()
