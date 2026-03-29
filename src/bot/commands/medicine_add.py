"""
Telegram bot command for adding medicine searches.
"""

from aiogram import Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove
from pharmaradar import Medicine, MedicineWatchdog

from src.bot.shared_utils import (
    abort_and_skip_keyboard,
    abort_keyboard,
    id_keyboard,
    is_abort,
    is_skip,
)
from src.bot.validation_utils import validate_float, validate_str
from src.logger import log


class AddMedicineStates(StatesGroup):
    choosing_name = State()
    choosing_dosage = State()
    choosing_amount = State()
    choosing_location = State()
    choosing_radius = State()
    choosing_max_price = State()
    choosing_min_availability = State()
    confirming = State()


def register_add_medicine_handler(dispatcher: Dispatcher, medicine_service: MedicineWatchdog):
    router = Router()
    command_name = "/medicine_add"

    @router.message(Command("medicine_add"))
    async def start_add_medicine(message: types.Message, state: FSMContext):
        """Start the add medicine conversation."""
        log.info(f"↪ Received command: {command_name}")
        if message.from_user:
            log.info(f"User {message.from_user.id} started adding medicine")
        await state.set_state(AddMedicineStates.choosing_name)
        await message.answer(
            "🏥 Add Medicine Search\n\nLet's add a new medicine to search for.\n\nWhat's the medicine name?",
            reply_markup=abort_keyboard(),
        )

    @router.message(AddMedicineStates.choosing_name)
    async def process_name(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await state.clear()
            await message.answer("❌ Cancelled adding medicine", reply_markup=ReplyKeyboardRemove())
            return

        if message.text and is_skip(message.text):
            await message.answer("❌ Medicine name is required", reply_markup=abort_and_skip_keyboard())
            return

        name = validate_str(message.text, min_length=1, max_length=100)
        if not name:
            await message.answer("❌ Invalid medicine name", reply_markup=abort_and_skip_keyboard())
            return

        await state.update_data(name=name)
        await state.set_state(AddMedicineStates.choosing_dosage)
        await message.answer(
            f"Medicine: {name}\n\nWhat's a single dosage? (e.g., 500 mg, 10 ml)\nSelect Skip if not applicable.",
            reply_markup=abort_and_skip_keyboard(),
        )

    @router.message(AddMedicineStates.choosing_dosage)
    async def process_dosage(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await state.clear()
            await message.answer("❌ Cancelled adding medicine", reply_markup=ReplyKeyboardRemove())
            return

        dosage = None
        if message.text and not is_skip(message.text):
            dosage = validate_str(message.text, min_length=1, max_length=50)
            if not dosage:
                await message.answer("❌ Invalid dosage format", reply_markup=abort_and_skip_keyboard())
                return

        await state.update_data(dosage=dosage)
        await state.set_state(AddMedicineStates.choosing_amount)
        await message.answer(
            "📦 What's the amount/quantity needed? (e.g., '30 tabl.', '100ml', '20 kaps.', optional):",
            reply_markup=abort_and_skip_keyboard(),
        )

    @router.message(AddMedicineStates.choosing_amount)
    async def process_amount(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await state.clear()
            await message.answer("❌ Cancelled adding medicine", reply_markup=ReplyKeyboardRemove())
            return

        amount = None
        if message.text and not is_skip(message.text):
            amount = validate_str(message.text, min_length=1, max_length=50)
            if not amount:
                await message.answer("❌ Invalid amount format", reply_markup=abort_and_skip_keyboard())
                return

        await state.update_data(amount=amount)
        await state.set_state(AddMedicineStates.choosing_location)
        await message.answer(
            "📍 What's the location (address or city) to search around? Format: city, street, e.g. Gdańsk, Warszawska.",
            reply_markup=abort_keyboard(),
        )

    @router.message(AddMedicineStates.choosing_location)
    async def process_location(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await state.clear()
            await message.answer("❌ Cancelled adding medicine", reply_markup=ReplyKeyboardRemove())
            return

        location = validate_str(message.text, min_length=1, max_length=200)
        if not location:
            await message.answer("❌ Invalid location", reply_markup=abort_and_skip_keyboard())
            return

        await state.update_data(location=location)
        await state.set_state(AddMedicineStates.choosing_radius)
        await message.answer(
            "📏 What's the search radius in kilometers? (default: 5.0)\nSelect Skip to use default.",
            reply_markup=abort_and_skip_keyboard(),
        )

    @router.message(AddMedicineStates.choosing_radius)
    async def process_radius(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await state.clear()
            await message.answer("❌ Cancelled adding medicine", reply_markup=ReplyKeyboardRemove())
            return

        radius_km = 5.0  # default
        if message.text and not is_skip(message.text):
            radius_km = validate_float(message.text, min_value=0.1, max_value=100.0)
            if radius_km is None:
                await message.answer(
                    "❌ Invalid radius (0.1-100 km)",
                    reply_markup=abort_and_skip_keyboard(),
                )
                return

        await state.update_data(radius_km=radius_km)
        await state.set_state(AddMedicineStates.choosing_max_price)
        await message.answer(
            "💰 What's the maximum price in zł? (optional)\nSelect Skip if no price limit.",
            reply_markup=abort_and_skip_keyboard(),
        )

    @router.message(AddMedicineStates.choosing_max_price)
    async def process_max_price(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await state.clear()
            await message.answer("❌ Cancelled adding medicine", reply_markup=ReplyKeyboardRemove())
            return

        max_price = None
        if message.text and not is_skip(message.text):
            max_price = validate_float(message.text, min_value=0.01, max_value=10000.0)
            if max_price is None:
                await message.answer(
                    "❌ Invalid price (0.01-10000 zł)",
                    reply_markup=abort_and_skip_keyboard(),
                )
                return

        await state.update_data(max_price=max_price)
        await state.set_state(AddMedicineStates.choosing_min_availability)

        availability_keyboard = id_keyboard(["low", "high", "none"], add_abort=True, add_skip=True)

        await message.answer(
            "📊 What's the minimum availability level?\n"
            "• low - low stock acceptable\n"
            "• high - high stock required\n"
            "• none - show even out of stock",
            reply_markup=availability_keyboard,
        )

    @router.message(AddMedicineStates.choosing_min_availability)
    async def process_min_availability(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await state.clear()
            await message.answer("❌ Cancelled adding medicine", reply_markup=ReplyKeyboardRemove())
            return

        min_availability = "low"  # default
        if message.text and not is_skip(message.text):
            if message.text not in ["low", "high", "none"]:
                await message.answer("❌ Please choose from the available options")
                return
            min_availability = message.text

        await state.update_data(min_availability=min_availability)
        await state.set_state(AddMedicineStates.confirming)

        data = await state.get_data()
        dosage_text = f" {data['dosage']}" if data.get("dosage") else ""
        amount_text = f" | {data['amount']}" if data.get("amount") else ""
        price_text = f"max {data['max_price']} zł, " if data.get("max_price") else ""

        confirmation_text = (
            f"🏥 Medicine Search Summary\n\n"
            f"💊 Medicine: {data['name']}{dosage_text}{amount_text}\n"
            f"📍 Location: {data['location']}\n"
            f"📏 Radius: {data['radius_km']} km\n"
            f"💰 Price: {price_text}min availability: {data['min_availability']}\n"
            f"\nConfirm adding this medicine search?"
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
            reply_markup=confirm_keyboard,
        )

    @router.message(AddMedicineStates.confirming)
    async def confirm_medicine(message: types.Message, state: FSMContext):
        if message.text == "❌ Cancel":
            await state.clear()
            await message.answer("❌ Cancelled adding medicine", reply_markup=ReplyKeyboardRemove())
            return

        if message.text != "✅ Confirm":
            await message.answer("Please choose ✅ Confirm or ❌ Cancel")
            return

        try:
            data = await state.get_data()
            medicine = Medicine(
                name=data["name"],
                dosage=data.get("dosage"),
                location=data["location"],
                radius_km=data["radius_km"],
                max_price=data.get("max_price"),
                min_availability=data["min_availability"],
                amount=data.get("amount"),
            )

            result = medicine_service.add_medicine(medicine)

            if result:
                await message.answer(
                    f"✅ Medicine search added successfully!\n\n💊 {medicine.full_name} in {data['location']}",
                    reply_markup=ReplyKeyboardRemove(),
                )
                if message.from_user:
                    log.info(f"User {message.from_user.id} added medicine: {medicine.full_name}")
                log.info(f"↩ Finished command: {command_name}")
            else:
                # Database operation failed
                await message.answer(
                    "❌ Error adding medicine search. Please try again.",
                    reply_markup=ReplyKeyboardRemove(),
                )
                if message.from_user:
                    log.error(f"User {message.from_user.id} failed to add medicine: {medicine.full_name}")
                log.info(f"↩ Failed command: {command_name}")

        except Exception as e:
            log.error(f"Error adding medicine: {str(e)}")
            await message.answer(
                "❌ Error adding medicine search. Please try again.",
                reply_markup=ReplyKeyboardRemove(),
            )
            log.info(f"↩ Failed command: {command_name}")

        await state.clear()

    dispatcher.include_router(router)
