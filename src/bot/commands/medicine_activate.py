"""
Telegram bot command for activating/deactivating medicine searches.
"""

from aiogram import Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from pharmaradar import MedicineWatchdog

from src.bot.shared_utils import escape_markdown, id_keyboard, is_abort
from src.bot.validation_utils import validate_int
from src.logger import log


class ActivateMedicineStates(StatesGroup):
    choosing_medicine_id = State()
    choosing_action = State()
    confirming = State()


def register_activate_medicine_handler(dispatcher: Dispatcher, medicine_service: MedicineWatchdog):
    router = Router()
    command_name = "/medicine_activate"

    @router.message(Command("medicine_activate"))
    async def start_activate_medicine(message: types.Message, state: FSMContext):
        """Start the activate/deactivate medicine conversation."""
        log.info(f"↪ Received command: {command_name}")
        if message.from_user:
            log.info(f"User {message.from_user.id} started activating/deactivating medicine")

        # Show available medicines
        medicines = medicine_service.get_all_medicines()

        if not medicines:
            await message.answer("📝 No medicine searches found\\.", parse_mode="MarkdownV2")
            log.info(f"↩ Finished command: {command_name} (no medicines found)")
            return

        medicines_text = "💊 *Available Medicine Searches:*\n\n"
        for medicine in medicines:
            dosage_text = f" {medicine.dosage}" if medicine.dosage else ""
            amount_text = f" {medicine.amount}" if medicine.amount else ""
            status_icon = "✅" if medicine.active else "❌"
            status_text = "Active" if medicine.active else "Inactive"

            medicines_text += (
                f"{status_icon} *{escape_markdown(str(medicine.id))}*\\. {escape_markdown(medicine.name)}{escape_markdown(dosage_text)}{escape_markdown(amount_text)}\n"
                f"📍 {escape_markdown(medicine.location)} \\({escape_markdown(str(medicine.radius_km))} km\\)\n"
                f"🏷️ Status: {status_text}\n\n"
            )

        medicines_text += "\n🔢 *Enter medicine ID* to activate/deactivate:"

        medicine_ids = [str(m.id) for m in medicines]

        await message.answer(medicines_text, parse_mode="MarkdownV2", reply_markup=id_keyboard(medicine_ids))
        await state.set_state(ActivateMedicineStates.choosing_medicine_id)

    @router.message(ActivateMedicineStates.choosing_medicine_id)
    async def process_medicine_id(message: types.Message, state: FSMContext):
        """Process the medicine ID selection."""
        if not message.text:
            await message.answer("❌ Invalid input\\. Please enter a medicine ID\\.", parse_mode="MarkdownV2")
            return

        user_input = message.text.strip()

        # Check for abort
        if is_abort(user_input):
            await message.answer(
                "❌ Medicine activation cancelled\\.", parse_mode="MarkdownV2", reply_markup=ReplyKeyboardRemove()
            )
            await state.clear()
            log.info(f"↩ Cancelled command: {command_name}")
            return

        # Validate medicine ID
        medicine_id = validate_int(user_input, min_value=1)
        if medicine_id is None:
            await message.answer("❌ Invalid ID\\. Please enter a valid medicine ID\\.", parse_mode="MarkdownV2")
            return

        # Check if medicine exists
        medicine = medicine_service.get_medicine(medicine_id)
        if not medicine:
            await message.answer(
                "❌ Medicine not found\\. Please enter a valid medicine ID\\.", parse_mode="MarkdownV2"
            )
            return

        # Store medicine ID in state
        await state.update_data(medicine_id=medicine_id)

        # Show current status and action options
        current_status = "Active" if medicine.active else "Inactive"
        status_icon = "✅" if medicine.active else "❌"

        medicine_info = (
            f"💊 *Selected Medicine:*\n\n"
            f"{escape_markdown(medicine.full_name)}\n"
            f"📍 {escape_markdown(medicine.location)} \\({escape_markdown(str(medicine.radius_km))} km\\)\n"
            f"{status_icon} Current Status: *{current_status}*\n\n"
            f"What would you like to do?"
        )

        # Create action keyboard
        activate_button = KeyboardButton(text="✅ Activate")
        deactivate_button = KeyboardButton(text="❌ Deactivate")
        abort_button = KeyboardButton(text="❌ Abort")

        action_keyboard = ReplyKeyboardMarkup(
            keyboard=[[activate_button, deactivate_button], [abort_button]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )

        await message.answer(medicine_info, parse_mode="MarkdownV2", reply_markup=action_keyboard)
        await state.set_state(ActivateMedicineStates.choosing_action)

    @router.message(ActivateMedicineStates.choosing_action)
    async def process_action(message: types.Message, state: FSMContext):
        """Process the activation/deactivation action."""
        if not message.text:
            await message.answer("❌ Invalid input\\. Please select an option\\.", parse_mode="MarkdownV2")
            return

        user_input = message.text.strip()

        # Check for abort
        if is_abort(user_input):
            await message.answer(
                "❌ Medicine activation cancelled\\.", parse_mode="MarkdownV2", reply_markup=ReplyKeyboardRemove()
            )
            await state.clear()
            log.info(f"↩ Cancelled command: {command_name}")
            return

        # Determine action
        if user_input in ["✅ Activate", "Activate"]:
            new_status = True
            action_text = "activate"
        elif user_input in ["❌ Deactivate", "Deactivate"]:
            new_status = False
            action_text = "deactivate"
        else:
            await message.answer(
                "❌ Invalid option\\. Please select Activate or Deactivate\\.", parse_mode="MarkdownV2"
            )
            return

        # Get medicine and check current status
        data = await state.get_data()
        medicine_id = data.get("medicine_id")
        if not isinstance(medicine_id, int):
            await message.answer(
                "❌ Invalid medicine ID\\.", parse_mode="MarkdownV2", reply_markup=ReplyKeyboardRemove()
            )
            await state.clear()
            return

        medicine = medicine_service.get_medicine(medicine_id)

        if not medicine:
            await message.answer(
                "❌ Medicine not found\\.", parse_mode="MarkdownV2", reply_markup=ReplyKeyboardRemove()
            )
            await state.clear()
            return

        # Check if action is needed
        if medicine.active == new_status:
            status_text = "active" if new_status else "inactive"
            await message.answer(
                f"ℹ️ Medicine is already {status_text}\\.", parse_mode="MarkdownV2", reply_markup=ReplyKeyboardRemove()
            )
            await state.clear()
            log.info(f"↩ Finished command: {command_name} (no change needed)")
            return

        # Store action in state
        await state.update_data(new_status=new_status, action_text=action_text)

        # Confirm action
        confirm_text = (
            f"💊 *Confirm Action:*\n\n"
            f"{escape_markdown(medicine.full_name)}\n"
            f"📍 {escape_markdown(medicine.location)}\n\n"
            f"❓ Are you sure you want to *{escape_markdown(action_text)}* this medicine search?"
        )

        confirm_button = KeyboardButton(text=f"✅ Yes, {action_text}")
        cancel_button = KeyboardButton(text="❌ Cancel")

        confirm_keyboard = ReplyKeyboardMarkup(
            keyboard=[[confirm_button], [cancel_button]], resize_keyboard=True, one_time_keyboard=True
        )

        await message.answer(confirm_text, parse_mode="MarkdownV2", reply_markup=confirm_keyboard)
        await state.set_state(ActivateMedicineStates.confirming)

    @router.message(ActivateMedicineStates.confirming)
    async def confirm_action(message: types.Message, state: FSMContext):
        """Confirm and execute the activation/deactivation."""
        if not message.text:
            await message.answer("❌ Invalid input\\. Please select an option\\.", parse_mode="MarkdownV2")
            return

        user_input = message.text.strip()
        data = await state.get_data()
        medicine_id = data.get("medicine_id")
        new_status = data.get("new_status")
        action_text = data.get("action_text")

        try:
            if user_input.startswith("✅ Yes"):
                # Validate medicine_id type
                if not isinstance(medicine_id, int):
                    await message.answer(
                        "❌ Invalid medicine ID\\.", parse_mode="MarkdownV2", reply_markup=ReplyKeyboardRemove()
                    )
                    await state.clear()
                    return

                # Get medicine
                medicine = medicine_service.get_medicine(medicine_id)
                if not medicine:
                    await message.answer(
                        "❌ Medicine not found\\.", parse_mode="MarkdownV2", reply_markup=ReplyKeyboardRemove()
                    )
                    log.info(f"↩ Failed command: {command_name} (medicine not found)")
                    await state.clear()
                    return

                # Update medicine status
                if isinstance(new_status, bool):
                    medicine.active = new_status
                success = medicine_service.update_medicine(medicine)

                if success:
                    status_icon = "✅" if new_status else "❌"
                    status_text = "activated" if new_status else "deactivated"

                    await message.answer(
                        f"{status_icon} Medicine search *{escape_markdown(status_text)}* successfully\\!\n\n"
                        f"💊 {escape_markdown(medicine.full_name)}\n"
                        f"📍 {escape_markdown(medicine.location)}",
                        parse_mode="MarkdownV2",
                        reply_markup=ReplyKeyboardRemove(),
                    )

                    if message.from_user:
                        log.info(f"User {message.from_user.id} {status_text} medicine: {medicine.full_name}")
                    log.info(f"↩ Finished command: {command_name}")
                else:
                    await message.answer(
                        f"❌ Failed to {escape_markdown(action_text or 'update')} medicine search\\.",
                        parse_mode="MarkdownV2",
                        reply_markup=ReplyKeyboardRemove(),
                    )
                    log.info(f"↩ Failed command: {command_name}")
            else:
                await message.answer(
                    f"❌ Medicine {escape_markdown(action_text or 'update')} cancelled\\.",
                    parse_mode="MarkdownV2",
                    reply_markup=ReplyKeyboardRemove(),
                )
                log.info(f"↩ Cancelled command: {command_name}")

        except Exception as e:
            log.error(f"Error {action_text or 'updating'}ing medicine: {str(e)}")
            await message.answer(
                f"❌ Error {escape_markdown(action_text or 'updating')}ing medicine search\\. Please try again\\.",
                parse_mode="MarkdownV2",
                reply_markup=ReplyKeyboardRemove(),
            )

        await state.clear()

    dispatcher.include_router(router)
