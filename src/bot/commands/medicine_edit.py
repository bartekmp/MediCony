"""
Telegram bot command for editing medicine searches.
"""

from aiogram import Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove
from pharmaradar import Medicine, MedicineWatchdog

from src.bot.shared_utils import (
    abort_and_skip_keyboard,
    escape_markdown,
    format_current_value,
    id_keyboard,
    is_abort,
    is_skip,
)
from src.bot.validation_utils import validate_float, validate_int, validate_str
from src.logger import log


def get_medicine_by_id(medicines, id_: str) -> Medicine | None:
    for m in medicines:
        if str(m.id) == id_:
            return m
    return None


class EditMedicineStates(StatesGroup):
    choosing_medicine_id = State()
    choosing_name = State()
    choosing_dosage = State()
    choosing_amount = State()
    choosing_location = State()
    choosing_radius = State()
    choosing_max_price = State()
    choosing_min_availability = State()
    confirming = State()


def register_edit_medicine_handler(dispatcher: Dispatcher, medicine_service: MedicineWatchdog):
    router = Router()
    command_name = "/medicine_edit"

    @router.message(Command("medicine_edit"))
    async def start_edit_medicine(message: types.Message, state: FSMContext):
        """Start the edit medicine conversation."""
        log.info(f"↪ Received command: {command_name}")
        if message.from_user:
            log.info(f"User {message.from_user.id} started editing medicine")

        # Show available medicines
        medicines = medicine_service.get_all_medicines()

        if not medicines:
            await message.answer("📝 No medicine searches found to edit.")
            log.info(f"↩ Finished command: {command_name} (no medicines found)")
            return

        medicines_text = "💊 Available Medicine Searches:\n\n"
        for medicine in medicines:
            dosage_text = f" {medicine.dosage}" if medicine.dosage else ""
            medicines_text += f"{medicine.id}. {medicine.name} {dosage_text}\n"
            medicines_text += f"📍 {medicine.location}\n\n"

        await state.set_state(EditMedicineStates.choosing_medicine_id)
        await message.answer(
            f"{medicines_text}Enter the medicine ID to edit:",
            reply_markup=id_keyboard([str(m.id) for m in medicines]),
        )

    @router.message(EditMedicineStates.choosing_medicine_id)
    async def process_medicine_id(message: types.Message, state: FSMContext):
        if is_abort(message.text or ""):
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            await message.answer("❌ Cancelled editing medicine", reply_markup=ReplyKeyboardRemove())
            return

        medicine_id = validate_int(message.text or "", min_value=1)
        if medicine_id is None:
            await message.answer(
                "❌ Invalid medicine ID",
                reply_markup=id_keyboard([str(m.id) for m in medicine_service.get_all_medicines()]),
            )
            return

        # Check if medicine exists
        medicine = medicine_service.get_medicine(medicine_id)
        if not medicine:
            await message.answer(
                f"❌ Medicine with ID {medicine_id} not found",
                reply_markup=id_keyboard([str(m.id) for m in medicine_service.get_all_medicines()]),
            )
            return

        await state.update_data(medicine_id=medicine_id, medicine=medicine)

        dosage_text = f" {medicine.dosage}" if medicine.dosage else ""
        price_text = f", max {medicine.max_price} zł" if medicine.max_price else ""

        # Show medicine details and edit options
        edit_options = [
            "name",
            "dosage",
            "amount",
            "location",
            "radius_km",
            "max_price",
            "min_availability",
        ]

        edit_keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text=option) for option in edit_options[:2]],
                [types.KeyboardButton(text=option) for option in edit_options[2:4]],
                [types.KeyboardButton(text=option) for option in edit_options[4:6]],
                [types.KeyboardButton(text=option) for option in edit_options[6:8]],
                [types.KeyboardButton(text="❌ Cancel")],
            ],
            resize_keyboard=True,
        )

        medicine_details = (
            f"*Current Medicine Details:*\n\n"
            f"💊 *{escape_markdown(medicine.name)}{escape_markdown(dosage_text)}* \\(ID: {medicine.id}\\)\n"
            f"📍 {escape_markdown(medicine.location)}\n"
            f"📏 Radius: {medicine.radius_km} km\n"
            f"📊 Min availability: {medicine.min_availability}{price_text}\n"
        )

        await message.answer(
            f"{medicine_details}\nChoose a field to edit:",
            reply_markup=edit_keyboard,
        )

        # Clear state and wait for field selection
        await state.set_state(None)

    @router.message(
        lambda message: message.text
        in ["name", "dosage", "amount", "location", "radius_km", "max_price", "min_availability"]
    )
    async def process_field_selection(message: types.Message, state: FSMContext):
        if not message.text:
            await message.answer("❌ Invalid field selected", reply_markup=ReplyKeyboardRemove())
            return

        # Get selected field
        field = message.text

        # Get medicine data
        data = await state.get_data()
        medicine = data.get("medicine")

        if not medicine:
            await message.answer("❌ Error: Medicine not found. Please start over.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            log.info(f"↩ Failed command: {command_name} (medicine not found)")
            return

        # Set state based on field
        field_state_map = {
            "name": EditMedicineStates.choosing_name,
            "dosage": EditMedicineStates.choosing_dosage,
            "amount": EditMedicineStates.choosing_amount,
            "location": EditMedicineStates.choosing_location,
            "radius_km": EditMedicineStates.choosing_radius,
            "max_price": EditMedicineStates.choosing_max_price,
            "min_availability": EditMedicineStates.choosing_min_availability,
        }

        next_state = field_state_map.get(field)
        if not next_state:
            await message.answer("❌ Invalid field selected", reply_markup=ReplyKeyboardRemove())
            return

        await state.update_data(field=field)
        await state.set_state(next_state)

        # Prepare prompts based on field
        field_prompts = {
            "name": f"Enter new name {format_current_value(medicine.name)}:",
            "dosage": f"Enter new dosage {format_current_value(medicine.dosage or 'None')}:",
            "amount": f"Enter new amount {format_current_value(medicine.amount or 'None')}:",
            "location": f"Enter new location {format_current_value(medicine.location)}:",
            "radius_km": f"Enter new radius in km {format_current_value(medicine.radius_km)}:",
            "max_price": f"Enter new max price {format_current_value(medicine.max_price or 'None')}:",
            "min_availability": (
                f"Enter new min availability level {format_current_value(medicine.min_availability)}\n(low, high, none):"
            ),
        }

        await message.answer(
            field_prompts.get(field, "Enter new value:"),
            reply_markup=abort_and_skip_keyboard(),
        )

    @router.message(EditMedicineStates.choosing_name)
    async def process_name(message: types.Message, state: FSMContext):
        if is_abort(message.text or ""):
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            await message.answer("❌ Cancelled editing medicine", reply_markup=ReplyKeyboardRemove())
            return

        if is_skip(message.text or ""):
            await message.answer("❌ Medicine name cannot be empty", reply_markup=abort_and_skip_keyboard())
            return

        name = validate_str(message.text or "", min_length=1, max_length=100)
        if not name:
            await message.answer("❌ Invalid medicine name", reply_markup=abort_and_skip_keyboard())
            return

        await state.update_data(new_name=name)
        await update_medicine_and_notify(message, state, medicine_service, command_name)

    @router.message(EditMedicineStates.choosing_dosage)
    async def process_dosage(message: types.Message, state: FSMContext):
        if is_abort(message.text or ""):
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            await message.answer("❌ Cancelled editing medicine", reply_markup=ReplyKeyboardRemove())
            return

        dosage = None
        if not is_skip(message.text or ""):
            dosage = validate_str(message.text or "", min_length=1, max_length=50)
            if not dosage:
                await message.answer("❌ Invalid dosage format", reply_markup=abort_and_skip_keyboard())
                return

        await state.update_data(new_dosage=dosage)
        await update_medicine_and_notify(message, state, medicine_service, command_name)

    @router.message(EditMedicineStates.choosing_amount)
    async def process_amount(message: types.Message, state: FSMContext):
        if is_abort(message.text or ""):
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            await message.answer("❌ Cancelled editing medicine", reply_markup=ReplyKeyboardRemove())
            return

        amount = None
        if not is_skip(message.text or ""):
            amount = validate_str(message.text or "", min_length=1, max_length=50)
            if not amount:
                await message.answer("❌ Invalid amount format", reply_markup=abort_and_skip_keyboard())
                return

        await state.update_data(new_amount=amount)
        await update_medicine_and_notify(message, state, medicine_service, command_name)

    @router.message(EditMedicineStates.choosing_location)
    async def process_location(message: types.Message, state: FSMContext):
        if is_abort(message.text or ""):
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            await message.answer("❌ Cancelled editing medicine", reply_markup=ReplyKeyboardRemove())
            return

        if is_skip(message.text or ""):
            await message.answer("❌ Location cannot be empty", reply_markup=abort_and_skip_keyboard())
            return

        location = validate_str(message.text or "", min_length=1, max_length=100)
        if not location:
            await message.answer("❌ Invalid location", reply_markup=abort_and_skip_keyboard())
            return

        await state.update_data(new_location=location)
        await update_medicine_and_notify(message, state, medicine_service, command_name)

    @router.message(EditMedicineStates.choosing_radius)
    async def process_radius(message: types.Message, state: FSMContext):
        if is_abort(message.text or ""):
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            await message.answer("❌ Cancelled editing medicine", reply_markup=ReplyKeyboardRemove())
            return

        if is_skip(message.text or ""):
            await message.answer("❌ Radius cannot be empty", reply_markup=abort_and_skip_keyboard())
            return

        radius_km = validate_float(message.text or "", min_value=0.1, max_value=100.0)
        if radius_km is None:
            await message.answer(
                "❌ Invalid radius (must be between 0.1 and 100 km)", reply_markup=abort_and_skip_keyboard()
            )
            return

        await state.update_data(new_radius_km=radius_km)
        await update_medicine_and_notify(message, state, medicine_service, command_name)

    @router.message(EditMedicineStates.choosing_max_price)
    async def process_max_price(message: types.Message, state: FSMContext):
        if is_abort(message.text or ""):
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            await message.answer("❌ Cancelled editing medicine", reply_markup=ReplyKeyboardRemove())
            return

        max_price = None
        if not is_skip(message.text or ""):
            max_price = validate_float(message.text or "", min_value=0.01, max_value=10000.0)
            if max_price is None:
                await message.answer(
                    "❌ Invalid price (must be between 0.01 and 10000)", reply_markup=abort_and_skip_keyboard()
                )
                return

        await state.update_data(new_max_price=max_price)
        await update_medicine_and_notify(message, state, medicine_service, command_name)

    @router.message(EditMedicineStates.choosing_min_availability)
    async def process_min_availability(message: types.Message, state: FSMContext):
        if is_abort(message.text or ""):
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            await message.answer("❌ Cancelled editing medicine", reply_markup=ReplyKeyboardRemove())
            return

        if is_skip(message.text or ""):
            await message.answer("❌ Min availability cannot be empty", reply_markup=abort_and_skip_keyboard())
            return

        valid_availability = ["low", "high", "none"]
        min_availability = message.text.lower() if message.text else None

        if min_availability not in valid_availability:
            await message.answer(
                "❌ Invalid availability level. Must be one of: low, high, none",
                reply_markup=abort_and_skip_keyboard(),
            )
            return

        await state.update_data(new_min_availability=min_availability)
        await update_medicine_and_notify(message, state, medicine_service, command_name)

    async def update_medicine_and_notify(message, state, medicine_service, command_name):
        """Update medicine with new values and notify the user."""
        try:
            data = await state.get_data()
            medicine_id = data.get("medicine_id")
            medicine = data.get("medicine")
            field = data.get("field")

            if not medicine_id or not medicine or not field:
                await message.answer("❌ Error: Missing data", reply_markup=ReplyKeyboardRemove())
                await state.clear()
                log.info(f"↩ Failed command: {command_name} (missing data)")
                return

            # Get the new value based on field
            data_key = f"new_{field}"
            if data_key not in data:
                await message.answer("❌ Error: Missing value for field", reply_markup=ReplyKeyboardRemove())
                await state.clear()
                log.info(f"↩ Failed command: {command_name} (missing value)")
                return

            new_value = data.get(data_key)

            # Update the medicine
            update_params = {field: new_value}

            success = medicine_service.update_medicine_fields(medicine_id, **update_params)

            if success:
                # Get updated medicine
                updated_medicine = medicine_service.get_medicine(medicine_id)

                if updated_medicine:
                    field_display_names = {
                        "name": "Name",
                        "dosage": "Dosage",
                        "amount": "Amount",
                        "location": "Location",
                        "radius_km": "Radius",
                        "max_price": "Max price",
                        "min_availability": "Min availability",
                    }

                    display_name = field_display_names.get(field, field)
                    old_value = getattr(medicine, field, "None")

                    await message.answer(
                        f"✅ Medicine updated successfully!\n\n"
                        f"💊 {updated_medicine.full_name}\n"
                        f"✏️ Changed {display_name}: "
                        f"{str(old_value)} → {str(new_value)}",
                        reply_markup=ReplyKeyboardRemove(),
                    )

                    log.info(f"User {message.from_user.id} updated medicine {medicine_id}: {field}={new_value}")
                    log.info(f"↩ Finished command: {command_name}")
                else:
                    await message.answer(
                        "✅ Medicine updated but could not retrieve updated details.",
                        reply_markup=ReplyKeyboardRemove(),
                    )
                    log.info(f"↩ Finished command: {command_name} (partial success)")
            else:
                await message.answer(
                    "❌ Failed to update medicine.",
                    reply_markup=ReplyKeyboardRemove(),
                )
                log.info(f"↩ Failed command: {command_name} (update failed)")

        except Exception as e:
            log.error(f"Error updating medicine: {str(e)}")
            await message.answer(
                "❌ Error updating medicine. Please try again.",
                reply_markup=ReplyKeyboardRemove(),
            )
            log.info(f"↩ Failed command: {command_name} (exception)")

        await state.clear()

    # Handle cancel button
    @router.message(lambda message: message.text == "❌ Cancel")
    async def cancel_edit(message: types.Message, state: FSMContext):
        await state.clear()
        log.info(f"↩ Aborted command: {command_name}")
        await message.answer("❌ Cancelled editing medicine", reply_markup=ReplyKeyboardRemove())

    dispatcher.include_router(router)
