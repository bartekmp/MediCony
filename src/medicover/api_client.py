import datetime
from typing import Dict, Tuple

from src.http_client import HTTPClient
from src.logger import log
from src.medicover.appointment import Appointment
from src.medicover.auth import Authenticator
from src.medicover.matchers import is_excluded, match_single_appointment, match_single_appointment_to_be_canceled
from src.medicover.watch import Watch, WatchExclusions, WatchType


class MediAPI:
    """Medicover API client with optional multi-account support.

    By default behaves as single-account (pass an Authenticator).
    Additional accounts can be registered via add_account(); switch with use_account().
    """

    def __init__(self, authenticator: Authenticator, alias: str = "default"):
        self._accounts: Dict[str, Tuple[Authenticator, HTTPClient]] = {}
        self.current_alias: str = alias
        self._add_account_internal(alias, authenticator)
        self.http_client = self._accounts[self.current_alias][1]

    # --- Account management ---
    def _add_account_internal(self, alias: str, authenticator: Authenticator):
        if alias not in self._accounts:
            self._accounts[alias] = (authenticator, HTTPClient(authenticator))

    def add_account(self, alias: str, username: str, password: str):
        self._add_account_internal(alias, Authenticator(f"{username}:{password}"))

    async def use_account(self, alias: str):
        if alias not in self._accounts:
            raise ValueError(f"Unknown account alias: {alias}")
        self.current_alias = alias
        self.http_client = self._accounts[alias][1]
        if self.http_client.headers is None:
            await self.http_client.auth()

    async def authenticate(self):
        if self.http_client.headers is None:
            await self.http_client.auth()

    async def find_appointments(
        self,
        region: int,
        city: str,
        specialty: int,
        clinic: int | None,
        start_date_time: datetime.date,
        doctor: int | None = None,
        appointment_type: WatchType = WatchType.STANDARD,
        exclusions: WatchExclusions = None,
    ) -> list[Appointment] | None:
        appointment_url = "https://api-gateway-online24.medicover.pl/appointments/api/search-appointments/slots"

        params = {
            "RegionIds": region,
            "SpecialtyIds": specialty,
            "ClinicIds": clinic,
            "Page": 1,
            "PageSize": 5000,
            "StartTime": str(start_date_time),
            "SlotSearchType": appointment_type.value,
            "VisitType": "Center",
        }

        if doctor:
            params["DoctorIds"] = doctor

        response = await self.http_client.get(appointment_url, params)
        if not response:
            log.error(f"Error while fetching appointments, response: {response}")
            return None
        response = response.json()
        if "items" not in response:
            return None
        appointments = response["items"]
        if city != "any":
            appointments = filter(lambda x: True if city in x["clinic"]["name"] else False, appointments)
        appts = [Appointment(appointment) for appointment in appointments]
        appts = [ap for ap in appts if not is_excluded(ap, exclusions)]
        return appts

    async def book_appointment(
        self, appointment_to_book: Appointment, appointment_type: WatchType = WatchType.STANDARD
    ) -> Appointment | None:
        prices_url = "https://api-gateway-online24.medicover.pl/payment-gateway/api/v1/visit-prices"
        booking_url = "https://api-gateway-online24.medicover.pl/appointments/api/search-appointments/book-appointment"
        params = {
            "visitDate": appointment_to_book.date_time.isoformat(),
            "visitDetails": [
                {
                    "clinicId": str(appointment_to_book.clinic.id),
                    "doctorId": str(appointment_to_book.doctor.id),
                    "specialtyId": str(appointment_to_book.specialty.id),
                }
            ],
            "visitVariant": appointment_type.value,
        }
        response = await self.http_client.post(prices_url, params)
        if not response:
            log.error("Error while fetching appointment prices details")
            return None

        price = response[0].get("price", "")
        if price != "0,00 zł":
            log.error(f"Appointment price is not free: {price}. Will not book")
            return None

        booking_params = {
            "bookingString": appointment_to_book.booking_string,
            "metadata": {"appointmentSource": "Direct"},
        }
        response = await self.http_client.post(booking_url, booking_params)
        if not response:
            log.error("Unable to send booking request")
            return None

        appointment_to_book.booking_identifier = response.get("appointmentId", None)
        # Tag with current account alias for persistence
        try:
            appointment_to_book.account = self.current_alias
        except Exception:
            pass
        return appointment_to_book

    async def find_and_book_appointment(
        self,
        region: int,
        city: str,
        specialty: int,
        clinic: int,
        date: datetime.datetime,
        doctor: int,
        appointment_type: WatchType = WatchType.STANDARD,
        exact_time_match: bool = True,
        exact_date_match: bool = True,
    ) -> Appointment | None:
        found_appointments = await self.find_appointments(
            region, city, specialty, clinic, date, doctor, appointment_type
        )
        if not found_appointments:
            log.error("Error while fetching appointment details or appointment not found")
            return None

        appointment_to_book = match_single_appointment(
            specialty, clinic, doctor, date, found_appointments, exact_time_match, exact_date_match
        )
        if not appointment_to_book:
            log.error(f"No appointment found matching criteria: {specialty}, {clinic}, {doctor}, {date}")
            return None

        return await self.book_appointment(appointment_to_book, appointment_type)

    async def update_appointment_metadata(self, appointment: Appointment, db_id: int):
        filters = await self.find_filters(specialty=appointment.specialty.id)
        clinics = filters.get("clinics", {})
        specialties = filters.get("specialties", {})
        doctors = filters.get("doctors", {})
        appointment.clinic.value = [c.get("value") for c in clinics if c.get("id") == str(appointment.clinic.id)].pop()
        appointment.specialty.value = [
            s.get("value") for s in specialties if s.get("id") == str(appointment.specialty.id)
        ].pop()
        appointment.doctor.value = [d.get("value") for d in doctors if d.get("id") == str(appointment.doctor.id)].pop()
        appointment.database_row_id = db_id

    async def update_watch_metadata(self, watch: Watch):
        for spec_item in watch.specialty:
            spec_item.value = "N/A"
            filters = await self.find_filters(specialty=spec_item.id, region=watch.region.id, search_type=watch.type)
            regions = filters.get("regions", {})
            specialties = filters.get("specialties", {})

            region_name = [r.get("value") for r in regions if r.get("id") == str(watch.region.id)]
            specialty_name = [r.get("value") for r in specialties if r.get("id") == str(spec_item.id)]

            spec_item.value = "N/A"
            watch.region.value = "N/A"

            if region_name:
                watch.region.value = region_name.pop()

            if not specialty_name:
                if watch.type == WatchType.EXAMINATION:
                    log.warning(
                        f"Couldn't read the details for watch: {watch.id} of type {watch.type}, your account needs an admission to be able to search for examinations"
                    )
                else:
                    log.warning(
                        f"Human-readable data not found for watch: {watch.id}, most likely a temporary problem with the API"
                    )
            else:
                spec_item.value = specialty_name.pop()

            if watch.doctor:
                doctors = filters.get("doctors", {})
                doctor = [d.get("value") for d in doctors if d.get("id") == str(watch.doctor.id)]
                if doctor:
                    watch.doctor.value = doctor.pop()

            if watch.clinic:
                clinics = filters.get("clinics", {})
                clinic = [c.get("value") for c in clinics if c.get("id") == str(watch.clinic.id)]
                if clinic:
                    watch.clinic.value = clinic.pop()

    async def cancel_appointment(self, appointment: Appointment) -> bool:
        # First find the appointment using /appointments?AppointmentState=Planned endpoint on the server side
        list_planned_appointments_url = "https://api-gateway-online24.medicover.pl/appointments/api/person-appointments/appointments?AppointmentState=Planned&Page=1&PageSize=20"
        planned_appointments = await self.http_client.get(list_planned_appointments_url, {})
        if planned_appointments is not None and planned_appointments.status_code == 401:
            log.warning("Response 401. Re-authenticating")
            await self.http_client.re_auth()
            planned_appointments = await self.http_client.get(list_planned_appointments_url, {})

        if not planned_appointments:
            log.error("No such appointment found on the server side")
            return False

        planned_appointments_list = planned_appointments.json()["items"]
        cancel_string = match_single_appointment_to_be_canceled(appointment, planned_appointments_list)
        if not cancel_string:
            log.error("Couldn't extract the cancel ID from server for given appointment")
            return False

        # Now send a DELETE request with the cancel_string
        cancel_url = "https://api-gateway-online24.medicover.pl/appointments/api/person-appointments/appointments/"
        response = await self.http_client.delete(f"{cancel_url}{cancel_string}")
        if response["status"] == "Success":
            return True
        else:
            log.error(f"Couldn't cancel the appointment, error: {response['errorDetails']}")
            return False

    async def find_filters(
        self, region: int | None = None, specialty: int | None = None, search_type: WatchType = WatchType.STANDARD
    ) -> dict:
        filters_url = "https://api-gateway-online24.medicover.pl/appointments/api/search-appointments/filters"
        params = {"SlotSearchType": search_type.value}
        if region:
            params["RegionIds"] = str(region)
        if specialty:
            params["SpecialtyIds"] = str(specialty)
        response = await self.http_client.get(filters_url, params)
        if response is not None and response.status_code == 401:
            log.warning("Response 401. Re-authenticating")
            await self.http_client.re_auth()
            response = await self.http_client.get(filters_url, params)
        if not response:
            return {}
        return response.json()


    # NOTE: No extra delegation needed; methods above always act on self.http_client which switches with use_account().
