"""
MedicoverApp module handling all Medicover-related functionality.
"""

import asyncio
from argparse import Namespace
from random import randint

from src.bot.telegram import notify
from src.config import MediConyConfig
from src.database import MedicoverDbClient
from src.id_value_util import IdValue
from src.logger import log
from src.medicover.api_client import MediAPI
from src.medicover.appointment import Appointment
from src.medicover.auth import Authenticator  # kept for backward compatibility / potential future removal
from src.medicover.matchers import match_within_date_range
from src.medicover.presenters import log_entities, log_entities_with_info
from src.medicover.services.watch_service import WatchService
from src.medicover.watch import Watch, WatchActiveStatus, WatchType, is_within


class MedicoverApp:
    """
    Handles all Medicover functionality including appointments, watches, etc.
    """

    def __init__(self, config: MediConyConfig, db_client: MedicoverDbClient, args: Namespace):
        """Initialize the Medicover application context."""
        # Core references
        self.config = config
        self.db_client = db_client
        self.args = args

        # Determine initial account alias (CLI supplied or default)
        self.default_account = getattr(args, "account", None) or config.medicover_default_account

        # Initialize MediAPI with default account authenticator and register others lazily
        user, pwd = config.get_account(self.default_account)
        self.api_client = MediAPI(Authenticator(f"{user}:{pwd}"), alias=self.default_account)
        # Register additional accounts for lazy use
        for alias, (u, p) in config.medicover_accounts.items():
            if alias != self.default_account:
                self.api_client.add_account(alias, u, p)

        # Services depending on API/DB
        self.watch_service = WatchService(self.api_client, self.db_client)  # type: ignore[arg-type]

    async def switch_account(self, alias: str):
        if alias == self.default_account:
            return
        await self.api_client.use_account(alias)
        self.default_account = alias

    async def authenticate(self):
        """Authenticate with Medicover API (ensures default account session)."""
        await self.api_client.authenticate()

    async def find_appointment(self):
        """Find appointments with the given parameters, log them and send a notification if requested."""
        log.info(
            f"Finding appointments for: (r: {self.args.region}, ci: {self.args.city}, s: {self.args.specialty},"
            f"cl: {self.args.clinic}, sd: {self.args.date}, d: {self.args.doctor}, E: {self.args.examination})"
        )
        if self.args.general_practitioner:
            self.args.specialty = (
                self.args.general_practitioner
            )  # Internal medicine, Family medicine, General practitioner internal IDs

        # If there are multiple specialties provided, iterate through them
        for spec in self.args.specialty:
            # Find appointments
            appointments = await self.api_client.find_appointments(
                self.args.region,
                self.args.city,
                spec,
                self.args.clinic,
                self.args.date,
                self.args.doctor,
                WatchType.EXAMINATION if self.args.examination else WatchType.STANDARD,
            )

            # Display appointments
            log_entities_with_info(appointments)

            if not appointments:
                return

            # Send notification if appointments are found
            if self.args.notification:
                title = self.args.title if str(self.args.title) else appointments[0].specialty.value
                notify(appointments, title)

    async def book_appointment(self):
        """Find and book an appointment with exact parameters provided by the user and log the result."""
        log.info(
            f"Booking appointment: ({self.args.region}, {self.args.specialty}, {self.args.clinic}, {self.args.date}, {self.args.doctor})"
        )
        result = await self.api_client.find_and_book_appointment(
            self.args.region,
            self.args.city,
            self.args.specialty,
            self.args.clinic,
            self.args.date,
            self.args.doctor,
            WatchType.EXAMINATION if self.args.examination else WatchType.STANDARD,
        )
        if not result:
            log.error("Error while booking appointment")
        else:
            # Save or mark (if already present) the appointment as booked in the database
            self.db_client.update_appointment(result)
            log.info(f"Booking result: {result.notification_str()}")

    async def list_filters(self):
        """List available filters based on the specified filter type."""
        log.info(f"Listing available filters for type: {self.args.filter_type}")
        if self.args.filter_type in ("doctors", "clinics"):
            # The "doctors" and "clinic" filters require region and specialty to be specified
            filters = await self.watch_service.list_available_filters(
                self.args.filter_type, region=self.args.region, specialty=self.args.specialty
            )
        elif self.args.filter_type == "examinations":
            # The "examination" filter requires region, specialty and a specific type to be provided
            filters = await self.watch_service.list_available_filters(
                self.args.filter_type,
                region=self.args.region,
                specialty=self.args.specialty,
                search_type=WatchType.EXAMINATION,
            )
        else:
            # Generic filter type, no additional parameters required
            filters = await self.watch_service.list_available_filters(self.args.filter_type)

        log.info("[ID] - [Value]")
        for r in filters:
            log.info(f"{r['id']} - {r['value']}")

    def add_watch(self):
        """Add a new watch for appointment tracking."""
        args = self.args
        if args.general_practitioner:
            # If -GP/--general-practitioner is used, it means the watch has to have 3 specialty IDs:
            # Internal medicine, Family medicine, General practitioner internal IDs
            args.specialty = args.general_practitioner

        watch = self.watch_service.add_watch(
            region=args.region,
            city=args.city,
            specialty=args.specialty,
            clinic_id=args.clinic,
            doctor_id=args.doctor,
            start_date=args.start_date,
            end_date=args.end_date,
            time_range=args.time_range,
            auto_book=args.auto_book,
            exclusions=args.exclude,
            account=getattr(args, "account", None) or self.config.medicover_default_account,
        )

        log.info("Adding watch:")
        for line in str(watch).splitlines()[1:]:
            log.info(line)

    async def edit_watch(self):
        """Edit an existing watch."""
        log.info(f"Editing watch no. {self.args.id}")
        # Fetch the current watch for logging and value update
        watch = self.watch_service.get_watch(self.args.id)
        if not watch:
            log.error(f"No watch with ID: {self.args.id} was found")
            return

        # If clinic_id changed, update value from API for logging
        if self.args.clinic:
            clinics = await self.watch_service.list_available_filters(
                "clinics", region=watch.region.id, specialty=watch.specialty[0].id
            )
            clinic_value = next((c["value"] for c in clinics if int(c["id"]) == self.args.clinic), None)
            if clinic_value:
                log.info(f"Updated clinic name for ID {self.args.clinic}: {clinic_value}")

        # Log the changes
        log.info("Updated watch with following data:")
        if self.args.city:
            log.info(f"     City: {self.args.city}")
        if self.args.clinic:
            log.info(f"     Clinic: {self.args.clinic}")
        if self.args.start_date:
            log.info(f"     Start date: {self.args.start_date}")
        if self.args.end_date:
            log.info(f"     End date: {self.args.end_date}")
        if self.args.time_range:
            log.info(f"     Time range: {self.args.time_range}")
        if self.args.exclude:
            log.info(f"     Exclusions: {self.args.exclude}")
        if self.args.auto_book:
            log.info(f"     Autobook: {self.args.auto_book}")

        # Update via watch service
        if self.watch_service.update_watch(
            watch,
            city=self.args.city,
            clinic_id=self.args.clinic,
            start_date=self.args.start_date,
            end_date=self.args.end_date,
            time_range=self.args.time_range,
            exclusions=self.args.exclude,
            auto_book=self.args.auto_book,
            account=getattr(self.args, "account", None),
        ):
            log.info(f"Watch no. {watch.id} updated successfully.")
        else:
            log.error(f"Failed to update watch no. {watch.id}, it may not exist or the update failed.")

    def remove_watch(self):
        """Remove watch from the database by ID."""
        log.info(f"Removing watch no. {self.args.id}")
        if self.watch_service.remove_watch(self.args.id):
            log.info(f"Watch no. {self.args.id} removed successfully.")
        else:
            log.error(f"No watch with ID: {self.args.id} was found")

    async def list_watches(self):
        """Get all watches with metadata, log them and send a notification if requested."""
        log.info("Listing all watches")
        watches = await self.watch_service.get_all_watches()
        # Optional filtering by account alias from CLI
        if getattr(self.args, "account", None):
            alias = getattr(self.args, "account")
            watches = [w for w in watches if (w.account or self.config.medicover_default_account) == alias]
        if not watches:
            log.info("No watches found")
            return

        log_entities(watches)

        if self.args.notification:
            notify(watches, "Current Watches")

    async def list_appointments(self):
        """List all booked appointments."""
        log.info("Listing all booked appointments")
        booked_appointments = self.db_client.get_booked_appointments()
        if not booked_appointments:
            log.info("No booked appointments found in the database")
            return

        for id, ap in booked_appointments:
            await self.api_client.update_appointment_metadata(ap, id)

        extracted_appointment_list = [ap for _, ap in booked_appointments]
        log_entities(extracted_appointment_list)

    async def cancel_appointment(self):
        """Cancel a booked appointment by ID."""
        log.info(f"Canceling booked appointment with ID: {self.args.id}")
        # Retrieve all appointments marked as booked from the database
        booked_appointments = self.db_client.get_booked_appointments()
        # Find the right appointment to cancel by ID
        filtered_appointments_by_id: list[tuple[int, Appointment]] = list(
            filter(lambda x: x[0] == self.args.id, booked_appointments)
        )
        if not filtered_appointments_by_id:
            log.error(f"No appointment with ID: {self.args.id} was found")

        id, appointment_to_cancel = filtered_appointments_by_id[0]
        if appointment_to_cancel.account:
            await self.switch_account(appointment_to_cancel.account)
        # Send a DELETE cancel request
        if self.api_client.cancel_appointment(appointment_to_cancel):
            log.info(f"Appointment with ID: {id} was successfully canceled")
        else:
            log.error(f"Canceling appointment with ID {id} was unsuccessful")

    async def autobook_appointment(self, watch: Watch, specialty: IdValue, found_appointments: list[Appointment]):
        """Automatically book an appointment based on watch criteria."""
        # Check if watch is valid
        if not watch.start_date:
            log.error("Autobooking requires --start-date/-ds argument while adding a watch, skipping autobooking")
            return

        # Filter out appointments outside the book_start_date and book_end_date range
        matching_appointment = match_within_date_range(
            specialty.id,
            watch.clinic.id if watch.clinic else None,
            watch.doctor.id if watch.doctor else None,
            watch.start_date,
            watch.end_date,
            found_appointments,
        )
        # Autobooking, book first available appointment, if not, continue with next ones
        for appointment in matching_appointment:
            # Find appointments that are in the given watch time range
            if is_within(watch.time_range, appointment.date_time.time()):
                log.info("Autobooking appointment:")
                log_entities([appointment])

                result = await self.api_client.book_appointment(appointment)
                if not result:
                    log.error("Error while booking appointment, trying next")
                    continue

                # Save or mark the appointment as booked in the database
                self.db_client.update_appointment(result)
                # TODO: Don't remove the watch, just mark it as inactive, then apply retention after N days - good for debug purposes
                if not self.db_client.remove_watch(watch.id):
                    log.warning(f"Watch with ID {watch.id} was not removed from the database")

                log.info(f"Booking result: {result.notification_str()}")
                # Send notification about the booked appointment
                notify([result], "Autobooked appointment")
                break

        log.info("Finished autobooking")

    def filter_and_notify(self, watch: Watch, appointments: list[Appointment]):
        """Filter new appointments and send notifications if needed."""
        # Filter not seen appointments and update the database
        appointments = self.db_client.save_appointments_and_filter_old(appointments)
        # Filter appointments that match the watch time range
        appointments = [ap for ap in appointments if is_within(watch.time_range, ap.date_time.time())]
        # Display found appointments
        log_entities_with_info(appointments)
        # Send notification if any new matching appointments are found
        if appointments:
            notify(appointments, appointments[0].specialty.value)

    async def search_appointments(self):
        """Search for appointments based on watches."""
        log.info("=== Evaluating watches")
        # Retrieve all watches from the database
        watches = self.db_client.get_watches()
        if not watches:
            log.info("No watches found in the database, finishing search")
            return
        for watch in watches:
            log.info(f"Watch: {watch.short_str()}")
            if (active_status := watch.is_active()) != WatchActiveStatus.ACTIVE:
                log.info(f"Watch {watch.id} is {active_status}, skipping")
                continue

            # Switch account for this watch if needed
            target_alias = watch.account or self.config.medicover_default_account
            try:
                await self.switch_account(target_alias)
            except Exception as e:
                log.error(f"Failed switching to account {target_alias}: {e}")
                continue

            # Each watch can have multiple specialties, iterate through them and find appointments matching the criteria
            for specialty in watch.specialty:
                # Wait a random time between 2 and 10 seconds before checking the next watch to avoid Too many requests error
                await asyncio.sleep(randint(2, 10))
                # Find new appointments
                appointments = await self.api_client.find_appointments(
                    watch.region.id,
                    watch.city,
                    specialty.id,
                    watch.clinic.id if watch.clinic else None,
                    watch.start_date,
                    watch.doctor.id if watch.doctor else None,
                    watch.type,
                    watch.exclusions,
                )
                if not appointments:
                    await asyncio.sleep(randint(5, 15))
                    continue

                # If a watch has autobooking flag enabled and has a start date (and the end date optionally), try to find and book an appointment
                if watch.auto_book:
                    await self.autobook_appointment(watch, specialty, appointments)
                    break
                # Just print found appointments for a given watch
                else:
                    self.filter_and_notify(watch, appointments)

            # Cooldown between each watch evaluation, to avoid Too many requests error
            await asyncio.sleep(randint(10, 30))
