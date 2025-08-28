"""
Telegram bot command for listing medicine searches.
"""

from aiogram import Dispatcher, Router, types
from aiogram.filters import Command
from pharmaradar import MedicineWatchdog

from src.logger import log


def register_medicines_handler(dispatcher: Dispatcher, medicine_service: MedicineWatchdog):
    router = Router()
    command_name = "/medicine_list"

    @router.message(Command("medicine_list"))
    async def list_medicines(message: types.Message):
        """List all medicine searches."""
        try:
            log.info(f"↪ Received command: {command_name}")
            if message.from_user:
                log.info(f"User {message.from_user.id} requested medicine list")

            medicines = medicine_service.get_all_medicines()
            medicines = sorted(medicines, key=lambda m: m.id or 0)
            if not medicines:
                await message.answer("📝 No medicine searches found.\n\nUse /medicine_add to add one.")
                log.info(f"↩ Finished command: {command_name} (no medicines found)")
                return

            response = f"💊 Medicine Searches ({len(medicines)})\n\n"

            for medicine in medicines:
                dosage_text = f" {medicine.dosage}" if medicine.dosage else ""
                price_text = f", max {medicine.max_price} zł" if medicine.max_price else ""
                status_icon = "✅" if medicine.active else "❌"
                status_text = "Active" if medicine.active else "Inactive"

                response += (
                    f"{status_icon} ID: {medicine.id}\n"
                    f"💊 {medicine.name}{dosage_text}\n"
                    f"📍 {medicine.location} ({medicine.radius_km} km)\n"
                    f"📊 Min: {medicine.min_availability}{price_text}\n"
                    f"🏷️ Status: {status_text}\n"
                )

                if medicine.title:
                    response += f"🏷️ Title: {medicine.title}\n"

                response += "\n"

            # Split message if too long
            if len(response) > 4000:
                messages = []
                current_msg = f"💊 *Medicine Searches* ({len(medicines)})\n\n"

                for i, medicine in enumerate(medicines, 1):
                    dosage_text = f" | {medicine.dosage}" if medicine.dosage else ""
                    amount_text = f" | {medicine.amount}" if medicine.amount else ""
                    price_text = f", max {medicine.max_price} zł" if medicine.max_price else ""
                    status_icon = "✅" if medicine.active else "❌"
                    status_text = "Active" if medicine.active else "Inactive"

                    medicine_text = (
                        f"{status_icon} {i}. {medicine.name}{dosage_text}{amount_text} (ID: {medicine.id})\n"
                        f"📍 {medicine.location} ({medicine.radius_km} km)\n"
                        f"📊 Min: {medicine.min_availability}{price_text}\n"
                        f"🏷️ Status: {status_text}\n"
                    )

                    if medicine.title:
                        medicine_text += f"🏷️ Title: {medicine.title}\n"

                    medicine_text += "\n"

                    if len(current_msg + medicine_text) > 4000:
                        messages.append(current_msg)
                        current_msg = medicine_text
                    else:
                        current_msg += medicine_text

                if current_msg:
                    messages.append(current_msg)

                for msg in messages:
                    await message.answer(msg)
            else:
                await message.answer(response)

            log.info(f"↩ Finished command: {command_name}")

        except Exception as e:
            log.error(f"Error listing medicines: {str(e)}")
            await message.answer("❌ Error retrieving medicine list.")
            log.info(f"↩ Failed command: {command_name}")

    dispatcher.include_router(router)
