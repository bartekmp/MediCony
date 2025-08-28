"""
MedicineApp module handling all medicine-related functionality.
"""

import asyncio
from argparse import Namespace

from pharmaradar import AvailabilityLevel, Medicine, MedicineWatchdog

from src.bot.telegram import send_message
from src.database import PharmaDbClient
from src.logger import log


class MedicineApp:
    """
    Handles all medicine functionality including pharmacy search, medicine tracking, etc.
    """

    def __init__(self, config, db_client: PharmaDbClient, args: Namespace):
        self.config = config
        self.db_client = db_client
        self.medicine_service = MedicineWatchdog(db_client, log=log.logger)
        self.args = args

    def add_medicine(self):
        """Add a new medicine search."""
        if not self.args:
            log.error("No arguments provided for adding medicine")
            return

        medicine = Medicine(
            name=getattr(self.args, "name", ""),
            dosage=getattr(self.args, "dosage", None),
            amount=getattr(self.args, "amount", None),
            location=getattr(self.args, "location", ""),
            radius_km=getattr(self.args, "radius", 5.0),
            max_price=getattr(self.args, "max_price", None),
            min_availability=getattr(self.args, "min_availability", AvailabilityLevel.LOW),
            title=getattr(self.args, "title", None),
        )

        if self.medicine_service.add_medicine(medicine):
            log.info("Added medicine:")
            for line in str(medicine).splitlines():
                log.info(line)

    def remove_medicine(self):
        """Remove a medicine search."""
        if not self.args:
            log.error("No arguments provided for removing medicine")
            return

        medicine_id = getattr(self.args, "id", None)
        if medicine_id is None:
            log.error("No medicine ID provided")
            return

        medicine = self.medicine_service.get_medicine(medicine_id)

        if not medicine:
            log.error(f"No medicine with ID: {medicine_id} was found")
            return

        if self.medicine_service.remove_medicine(medicine_id):
            log.info(f"Removed medicine: {medicine.full_name}")
        else:
            log.error(f"Failed to remove medicine with ID: {medicine_id}")

    def list_medicines(self):
        """List all medicine searches."""
        medicines = self.medicine_service.get_all_medicines()

        if not medicines:
            log.info("No medicines found")
            return

        log.info(f"Found {len(medicines)} medicine(s):")
        for i, medicine in enumerate(medicines, 1):
            log.info(f"--- Medicine {i} (ID: {medicine.id}) ---")
            for line in str(medicine).splitlines():
                log.info("\t" + line)

        # Send notification if requested
        if self.args and getattr(self.args, "notification", False):
            # Create a custom notification for medicine list
            try:
                medicine_list = "\n\n".join([str(medicine) for medicine in medicines])
                send_message("Medicine List", medicine_list)
            except Exception as e:
                log.error(f"Failed to send Telegram notification: {str(e)}")

    def edit_medicine(self):
        """Edit an existing medicine search."""
        if not self.args:
            log.error("No arguments provided for editing medicine")
            return

        medicine_id = getattr(self.args, "id", None)
        if medicine_id is None:
            log.error("No medicine ID provided")
            return

        medicine = self.medicine_service.get_medicine(medicine_id)

        if not medicine:
            log.error(f"No medicine with ID: {medicine_id} was found")
            return

        log.info(f"Editing medicine ID {medicine_id}")

        # Get current medicine and update fields that are provided
        updated_medicine = Medicine(
            id=medicine.id,
            name=getattr(self.args, "name", medicine.name),
            dosage=getattr(self.args, "dosage", medicine.dosage),
            amount=getattr(self.args, "amount", medicine.amount),
            location=getattr(self.args, "location", medicine.location),
            radius_km=getattr(self.args, "radius", medicine.radius_km),
            max_price=getattr(self.args, "max_price", medicine.max_price),
            min_availability=getattr(self.args, "min_availability", medicine.min_availability),
            title=getattr(self.args, "title", medicine.title),
            last_search_at=medicine.last_search_at,
        )

        # Update the medicine
        if self.medicine_service.update_medicine(updated_medicine):
            # Get updated medicine for display
            updated_medicine = self.medicine_service.get_medicine(medicine_id)
            log.info("Medicine updated:")
            for line in str(updated_medicine).splitlines():
                log.info(line)
        else:
            log.error(f"Failed to update medicine with ID: {medicine_id}")

    async def search_medicine(self):
        """Search for a specific medicine."""
        if not self.args:
            log.error("No arguments provided for searching medicine")
            return

        medicine_id = getattr(self.args, "id", None)
        if medicine_id is None:
            log.error("No medicine ID provided")
            return

        medicine = self.medicine_service.get_medicine(medicine_id)

        if not medicine:
            log.error(f"No medicine with ID: {medicine_id} was found")
            return

        log.info(f"Searching for medicine: {medicine.full_name}")

        try:
            # Add timeout to prevent hanging
            pharmacies = await asyncio.wait_for(
                self.medicine_service.search_medicine(medicine), timeout=self.config.medicine_search_timeout_seconds
            )
        except asyncio.TimeoutError:
            log.error(
                f"Medicine search timed out after {self.config.medicine_search_timeout_seconds} seconds for: {medicine.full_name}"
            )
            return
        except Exception as search_error:
            log.error(f"Medicine search failed for {medicine.full_name}: {str(search_error)}")
            return

        if not pharmacies:
            log.info("No pharmacies found with available medicine")
            return

        log.info(f"Found {len(pharmacies)} pharmacy/pharmacies:")
        for i, pharmacy in enumerate(pharmacies, 1):
            log.info(f"\n--- Pharmacy {i} ---")
            for line in str(pharmacy).splitlines():
                log.info(line)

        # Send notification if requested
        if getattr(self.args, "notification", False):
            title = medicine.title if medicine.title else f"Medicine: {medicine.full_name}"
            try:
                pharmacy_list = "\n\n".join([str(pharmacy) for pharmacy in pharmacies])
                send_message(title, pharmacy_list)
            except Exception as e:
                log.error(f"Failed to send Telegram notification: {str(e)}")

    async def search_medicines(self):
        """Search for medicines based on medicine searches."""
        log.info("=== Evaluating medicines")

        try:
            # Get all medicines from database
            all_medicines = self.medicine_service.get_all_medicines()

            if not all_medicines:
                log.info("No medicines to search for")
                return

            # Filter only active medicines
            active_medicines = [m for m in all_medicines if m.active]

            if not active_medicines:
                log.info(
                    f"No active medicines to search for (found {len(all_medicines)} total, {len(all_medicines) - len(active_medicines)} inactive)"
                )
                return

            log.info(f"Found {len(active_medicines)} active medicine(s) to search (out of {len(all_medicines)} total)")

            for medicine in active_medicines:
                try:
                    log.info(f"MEDICINE: {medicine.full_name} near {medicine.location}")

                    # Search for medicine availability with timeout
                    try:
                        # Add timeout to medicine search to prevent hanging
                        pharmacies = await asyncio.wait_for(
                            self.medicine_service.search_medicine(medicine),
                            timeout=self.config.medicine_search_timeout_seconds,
                        )
                    except asyncio.TimeoutError:
                        log.warning(
                            f"Medicine search timed out after {self.config.medicine_search_timeout_seconds} seconds for: {medicine.full_name}"
                        )
                        continue
                    except Exception as search_error:
                        log.error(f"Medicine search failed for {medicine.full_name}: {str(search_error)}")
                        continue

                    if pharmacies:
                        log.info(f"Found {len(pharmacies)} pharmacy/pharmacies for {medicine.full_name}:")
                        for pharmacy in pharmacies:
                            log.info(f"   {pharmacy.name}: {pharmacy.availability}")

                        # Count pharmacies with at least low availability
                        available_pharmacies = [p for p in pharmacies if p.availability.is_available]

                        if len(available_pharmacies) >= 3:
                            log.info(
                                f"Medicine {medicine.full_name} found in {len(available_pharmacies)} pharmacies with availability, deactivating..."
                            )

                            # Deactivate the medicine
                            medicine.active = False
                            if self.medicine_service.update_medicine(medicine):
                                log.info(f"Successfully deactivated medicine: {medicine.full_name}")
                            else:
                                log.error(f"Failed to deactivate medicine: {medicine.full_name}")

                        # Send notification for medicine availability
                        try:
                            title = (
                                medicine.title
                                if medicine.title
                                else f"Medicine Available:\n{medicine.full_name}\nLocation: {medicine.location}\n\n"
                            )
                            pharmacy_list = "\n\n".join([str(pharmacy) for pharmacy in pharmacies])
                            send_message(title, pharmacy_list)
                            log.info(f"Sent notification for medicine: {medicine.full_name}")
                        except Exception as e:
                            log.error(f"Failed to send medicine notification: {str(e)}")
                    else:
                        log.info(f"No pharmacies found for {medicine.full_name}")

                    # Wait between medicine searches to avoid overwhelming the target website
                    await asyncio.sleep(5)

                except Exception as e:
                    log.error(f"Error searching medicine {medicine.full_name}: {str(e)}")
                    continue

        except Exception as e:
            log.error(f"Error in medicine search cycle: {str(e)}")
