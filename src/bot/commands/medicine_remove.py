"""
Telegram bot command for removing medicine searches.
"""

from aiogram import Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove
from pharmaradar import MedicineWatchdog

from src.bot.shared_utils import abort_and_skip_keyboard, escape_markdown, id_keyboard, is_abort
from src.bot.validation_utils import validate_int
from src.logger import log


class RemoveMedicineStates(StatesGroup):
    choosing_medicine_id = State()
    confirming = State()


def register_remove_medicine_handler(dispatcher: Dispatcher, medicine_service: MedicineWatchdog):
    router = Router()
    command_name = "/medicine_remove"

    @router.message(Command("medicine_remove"))
    async def start_remove_medicine(message: types.Message, state: FSMContext):
        """Start the remove medicine conversation."""
        log.info(f"↪ Received command: {command_name}")
        if message.from_user:
            log.info(f"User {message.from_user.id} started removing medicine")

        # Show available medicines
        medicines = medicine_service.get_all_medicines()

        if not medicines:
            await message.answer("📝 No medicine searches found to remove\\.", parse_mode="MarkdownV2")
            log.info(f"↩ Finished command: {command_name} (no medicines found)")
            return

        medicines_text = "💊 *Available Medicine Searches:*\n\n"
        sorted_medicines = sorted(medicines, key=lambda m: m.id or 0)
        for medicine in sorted_medicines:
            dosage_text = f" {medicine.dosage}" if medicine.dosage else ""
            medicines_text += f"*{medicine.id}\\. {escape_markdown(medicine.name)}{escape_markdown(dosage_text)}*\n"
            medicines_text += f"📍 {escape_markdown(medicine.location)}\n\n"

        await state.set_state(RemoveMedicineStates.choosing_medicine_id)
        await message.answer(
            f"{medicines_text}Enter or choose the medicine ID to remove:",
            parse_mode="MarkdownV2",
            reply_markup=id_keyboard([medicine.id for medicine in sorted_medicines]),
        )

    @router.message(RemoveMedicineStates.choosing_medicine_id)
    async def process_medicine_id(message: types.Message, state: FSMContext):
        if not message.text or (message.text and is_abort(message.text)):
            await state.clear()
            await message.answer("❌ Cancelled removing medicine", reply_markup=ReplyKeyboardRemove())
            return

        medicine_id = validate_int(message.text, min_value=1)
        if medicine_id is None:
            await message.answer("❌ Invalid medicine ID", reply_markup=abort_and_skip_keyboard())
            return

        # Check if medicine exists
        medicine = medicine_service.get_medicine(medicine_id)
        if not medicine:
            await message.answer(f"❌ Medicine with ID {medicine_id} not found", reply_markup=abort_and_skip_keyboard())
            return

        await state.update_data(medicine_id=medicine_id, medicine=medicine)
        await state.set_state(RemoveMedicineStates.confirming)

        dosage_text = f" {medicine.dosage}" if medicine.dosage else ""

        confirmation_text = (
            f"🗑️ Confirm Medicine Removal\n\n"
            f"💊 Medicine: {escape_markdown(medicine.name)}{escape_markdown(dosage_text)}\n"
            f"📍 Location: {escape_markdown(medicine.location)}\n"
            f"📏 Radius: {escape_markdown(str(medicine.radius_km))} km\n"
            f"\nAre you sure you want to remove this medicine search?"
        )

        confirm_keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="✅ Confirm")],
                [types.KeyboardButton(text="❌ Cancel")],
            ],
            resize_keyboard=True,
        )

        await message.answer(
            confirmation_text,
            parse_mode="MarkdownV2",
            reply_markup=confirm_keyboard,
        )

    @router.message(RemoveMedicineStates.confirming)
    async def confirm_removal(message: types.Message, state: FSMContext):
        if message.text == "❌ Cancel":
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            await message.answer("❌ Cancelled removing medicine", reply_markup=ReplyKeyboardRemove())
            return

        if message.text != "✅ Confirm":
            await message.answer("Please choose ✅ Confirm or ❌ Cancel")
            return

        try:
            data = await state.get_data()
            medicine_id = data["medicine_id"]
            medicine = data["medicine"]

            success = medicine_service.remove_medicine(medicine_id)

            if success:
                await message.answer(
                    f"✅ Medicine search removed successfully\\!\n\n" f"💊 {escape_markdown(medicine.full_name)}",
                    parse_mode="MarkdownV2",
                    reply_markup=ReplyKeyboardRemove(),
                )
                if message.from_user:
                    log.info(f"User {message.from_user.id} removed medicine: {medicine.full_name}")
                log.info(f"↩ Finished command: {command_name}")
            else:
                await message.answer(
                    "❌ Failed to remove medicine search\\.",
                    parse_mode="MarkdownV2",
                    reply_markup=ReplyKeyboardRemove(),
                )
                log.info(f"↩ Failed command: {command_name}")

        except Exception as e:
            log.error(f"Error removing medicine: {str(e)}")
            await message.answer(
                "❌ Error removing medicine search\\. Please try again\\.",
                parse_mode="MarkdownV2",
                reply_markup=ReplyKeyboardRemove(),
            )

        await state.clear()

    dispatcher.include_router(router)
