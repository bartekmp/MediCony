from aiogram import Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove

from src.config import get_config, MediConyConfig
from src.bot.shared_utils import (
    abort_and_skip_keyboard,
    abort_keyboard,
    ask_with_skip,
    escape_markdown,
    get_suggested_properties,
    id_keyboard,
    is_abort,
    is_skip,
    two_column_keyboard,
)
from src.bot.validation_utils import (
    validate_bool,
    validate_date,
    validate_date_difference,
    validate_date_not_in_past,
    validate_exclusions,
    validate_int,
    validate_str,
    validate_time_range,
)
from src.logger import log
from src.medicover.services.watch_service import WatchService
from src.medicover.watch import GENERAL_PRACTITIONER_SPECIALTIES, GENERAL_PRACTITIONER_SPECIALTIES_LABEL


class AddWatchStates(StatesGroup):
    choosing_account = State()
    choosing_region = State()
    choosing_city = State()
    choosing_specialty = State()
    choosing_doctor = State()
    choosing_start_date = State()
    choosing_end_date = State()
    choosing_time_range = State()
    choosing_auto_book = State()
    choosing_exclusions = State()
    choosing_type = State()
    confirming = State()


def register_add_watch_handler(dispatcher: Dispatcher, watch_service: WatchService, config: MediConyConfig | None = None):
    router = Router()
    command_name = "/watch_add"
    suggested = get_suggested_properties()
    if not config:
        config = get_config()
    account_aliases = config.list_account_aliases()

    @router.message(Command("watch_add"))
    async def handle_add_watch(message: types.Message, state: FSMContext):
        log.info(f"↪ Received command: {command_name}")
        log.info("Started adding new watch")
        # Multi-account selection flow
        if len(account_aliases) > 1:
            await message.answer(
                "👤 Choose account:",
                reply_markup=two_column_keyboard(account_aliases),
            )
            await state.set_state(AddWatchStates.choosing_account)
            return
        # Single account – go directly to region selection
        region_suggested = suggested.get("region")
        msg = "🌍 Enter region ID:"
        buttons = []
        if region_suggested:
            msg += f"\nSuggested choice: *{escape_markdown(region_suggested['label'])}*"
            buttons.append(region_suggested["label"])
        await message.answer(msg, reply_markup=abort_keyboard(extra_buttons=buttons), parse_mode="MarkdownV2")
        await state.set_state(AddWatchStates.choosing_region)

    # Conditionally register account choosing handler only if needed to preserve handler ordering for tests
    if len(account_aliases) > 1:
        @router.message(AddWatchStates.choosing_account)
        async def choose_account(message: types.Message, state: FSMContext):  # type: ignore
            alias = message.text.strip() if message.text else None
            if alias not in account_aliases:
                await message.answer("❌ Invalid alias. Choose one of the provided buttons.")
                return
            await state.update_data(account=alias)
            region_suggested = suggested.get("region")
            msg = "🌍 Enter region ID:"
            buttons = []
            if region_suggested:
                msg += f"\nSuggested choice: *{escape_markdown(region_suggested['label'])}*"
                buttons.append(region_suggested["label"])
            await message.answer(msg, reply_markup=abort_keyboard(extra_buttons=buttons), parse_mode="MarkdownV2")
            await state.set_state(AddWatchStates.choosing_region)

    @router.message(AddWatchStates.choosing_region)
    async def choose_region(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await message.answer("🚫 Adding aborted.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            return
        region_suggested = suggested.get("region")
        region_input = message.text
        # If user picked the suggested button, strip [name] if present
        if region_suggested and region_input == region_suggested["label"]:
            region_input = region_suggested["value"]
        region = validate_int(f"{region_input}")
        if region is None:
            msg = "❌ Invalid region ID. Please enter a valid integer number."
            buttons = []
            if region_suggested:
                msg += f"\nSuggested choice: *{escape_markdown(region_suggested['label'])}*"
                buttons.append(region_suggested["label"])
            await message.answer(
                msg, reply_markup=abort_and_skip_keyboard(extra_buttons=buttons), parse_mode="MarkdownV2"
            )
            return
        await state.update_data(region=region)
        city_suggested = suggested.get("city")
        msg = "🏙️ Enter city name or press *Skip*:"
        buttons = []
        if city_suggested:
            msg += f"\nSuggested choice: *{city_suggested}*"
            buttons.append(city_suggested)
        await message.answer(msg, reply_markup=abort_and_skip_keyboard(extra_buttons=buttons), parse_mode="MarkdownV2")
        await state.set_state(AddWatchStates.choosing_city)

    @router.message(AddWatchStates.choosing_city)
    async def choose_city(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await message.answer("🚫 Adding aborted.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            return

        city = None if message.text and is_skip(message.text) else validate_str(message.text)
        await state.update_data(city=city)
        region = (await state.get_data()).get("region")
        specialties = await watch_service.list_available_filters("specialties", region=region)
        if not specialties:
            await message.answer("❌ Couldn't get specialties.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            return

        specialty_names = [f"{s['id']}: {s['value']}" for s in specialties]
        # Add GP button at the top
        gp_label = GENERAL_PRACTITIONER_SPECIALTIES_LABEL
        keyboard_items = [gp_label] + specialty_names
        await message.answer(
            "💡 Available specialties:",
            reply_markup=two_column_keyboard(keyboard_items),
        )
        await message.answer(
            escape_markdown("▶️ Enter specialty ID or choose a button:"),
            parse_mode="MarkdownV2",
        )
        await state.set_state(AddWatchStates.choosing_specialty)

    @router.message(AddWatchStates.choosing_specialty)
    async def choose_specialty(message: types.Message, state: FSMContext):
        specialty = None
        if message.text and is_abort(message.text):
            await message.answer("🚫 Adding aborted.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            return
        if message.text and is_skip(message.text):
            specialty = None
        elif message.text:
            text = message.text.strip()
            if text == GENERAL_PRACTITIONER_SPECIALTIES_LABEL:
                specialty = GENERAL_PRACTITIONER_SPECIALTIES
            else:
                try:
                    specialty = [int(text.split(": ")[0].strip())]
                except Exception:
                    await message.answer(
                        escape_markdown("❌ Invalid specialty ID(s). Please enter valid ID(s) or Abort."),
                        reply_markup=abort_and_skip_keyboard(),
                    )
                    return
                if not specialty:
                    await message.answer(
                        escape_markdown("❌ No specialty ID provided. Please enter at least one ID or Abort."),
                        reply_markup=abort_and_skip_keyboard(),
                    )
                    return
        await state.update_data(specialty=specialty)
        data = await state.get_data()
        region = data.get("region")
        specialty_ids = data.get("specialty")
        # For doctor/clinic filter, use first specialty id if list
        specialty_id = specialty_ids[0] if isinstance(specialty_ids, list) and specialty_ids else specialty_ids
        doctors = await watch_service.list_available_filters("doctors", region=region, specialty=specialty_id)
        if available_doctors := "".join([f"  *{d['id']}* : {escape_markdown(d['value'])}\n" for d in doctors]):
            await message.answer("💡 Available doctors in given region:\n" + available_doctors, parse_mode="MarkdownV2")

        doctor_ids = [d["id"] for d in doctors] if doctors else []
        await message.answer(
            "▶️ Enter doctor ID or press *Skip*:",
            reply_markup=id_keyboard(doctor_ids, add_skip=True),
            parse_mode="MarkdownV2",
        )
        await state.set_state(AddWatchStates.choosing_doctor)

    @router.message(AddWatchStates.choosing_doctor)
    async def choose_doctor(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await message.answer("🚫 Adding aborted.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            return
        doctor = None
        if message.text and is_skip(message.text):
            doctor = None
        elif message.text:
            doctor = validate_int(message.text)
            if doctor is None:
                await message.answer(
                    "❌ Invalid doctor ID. Please enter a valid integer or press *Skip*.",
                    parse_mode="MarkdownV2",
                    reply_markup=abort_and_skip_keyboard(),
                )
                return

        await state.update_data(doctor=doctor)

        data = await state.get_data()
        region = data.get("region")
        specialty_ids = data.get("specialty")
        # For doctor/clinic filter, use first specialty id if list
        specialty_id = specialty_ids[0] if isinstance(specialty_ids, list) and specialty_ids else specialty_ids
        clinics = await watch_service.list_available_filters("clinics", region=region, specialty=specialty_id)
        if available_clinics := "".join([f"  *{c['id']}* : {escape_markdown(c['value'])}\n" for c in clinics]):
            await message.answer("💡 Available clinics in given region:\n" + available_clinics, parse_mode="MarkdownV2")

        clinic_ids = [c["id"] for c in clinics]
        await message.answer(
            "▶️ Enter new clinic ID or press *Skip*:",
            parse_mode="MarkdownV2",
            reply_markup=id_keyboard(clinic_ids, add_skip=True),
        )
        await state.set_state(AddWatchStates.choosing_start_date)

    @router.message(AddWatchStates.choosing_start_date)
    async def choose_clinic_and_start_date(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await message.answer("🚫 Adding aborted.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            return
        clinic = None
        if message.text and is_skip(message.text):
            clinic = None
        elif message.text:
            clinic = validate_int(message.text)
            if clinic is None:
                await message.answer(
                    "❌ Invalid clinic ID. Please enter a valid integer or press *Skip*.",
                    parse_mode="MarkdownV2",
                    reply_markup=abort_and_skip_keyboard(),
                )
                return

        await state.update_data(clinic=clinic)
        await ask_with_skip(message, "start date", "YYYY-MM-DD")
        await state.set_state(AddWatchStates.choosing_end_date)

    @router.message(AddWatchStates.choosing_end_date)
    async def choose_start_date(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await message.answer("🚫 Adding aborted.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            return
        start_date = None
        if message.text and is_skip(message.text):
            start_date = None
        elif message.text:
            start_date = validate_date(message.text)
            if message.text and start_date is None:
                await message.answer(
                    escape_markdown("❌ Invalid date format. Please enter as YYYY-MM-DD or press *Skip*."),
                    parse_mode="MarkdownV2",
                    reply_markup=abort_and_skip_keyboard(),
                )
                return
            if start_date and validate_date_not_in_past(start_date.isoformat()) is None:
                await message.answer(
                    escape_markdown("❌ Date cannot be in the past. Please enter a valid date or press *Skip*."),
                    parse_mode="MarkdownV2",
                    reply_markup=abort_and_skip_keyboard(),
                )
                return

        await state.update_data(start_date=start_date)
        await ask_with_skip(message, "end date", "YYYY-MM-DD")
        await state.set_state(AddWatchStates.choosing_time_range)

    @router.message(AddWatchStates.choosing_time_range)
    async def choose_end_date(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await message.answer("🚫 Adding aborted.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            return

        data = await state.get_data()
        start_date = data.get("start_date")
        end_date = None
        if message.text and is_skip(message.text):
            end_date = None
        elif message.text:
            end_date = validate_date(message.text)
            if message.text and end_date is None:
                await message.answer(
                    escape_markdown("❌ Invalid date format. Please enter as YYYY-MM-DD or press *Skip*."),
                    parse_mode="MarkdownV2",
                    reply_markup=abort_and_skip_keyboard(),
                )
                return
            if end_date and start_date and not validate_date_difference(str(start_date), end_date.isoformat()):
                await message.answer(
                    escape_markdown(
                        "❌ End date cannot be earlier than start date. Please enter a valid end date or press *Skip*."
                    ),
                    parse_mode="MarkdownV2",
                    reply_markup=abort_and_skip_keyboard(),
                )
                return
            if end_date and validate_date_not_in_past(end_date.isoformat()) is None:
                await message.answer(
                    escape_markdown(
                        "❌ End date cannot be in the past. Please enter a valid end date or press *Skip*."
                    ),
                    parse_mode="MarkdownV2",
                    reply_markup=abort_and_skip_keyboard(),
                )
                return

        await state.update_data(end_date=end_date)
        await ask_with_skip(message, "time range", "HH:MM-HH:MM, or just HH:MM for endless (up to 23:59:59)")
        await state.set_state(AddWatchStates.choosing_auto_book)

    @router.message(AddWatchStates.choosing_auto_book)
    async def choose_time_range(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await message.answer("🚫 Adding aborted.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            return
        tr = None
        if message.text and is_skip(message.text):
            tr = None
        elif message.text:
            tr = validate_time_range(message.text)
            if message.text and tr is None:
                await message.answer(
                    escape_markdown(
                        "❌ Invalid time range format. Please enter as HH:MM:SS[-HH:MM:SS] or press *Skip*."
                    ),
                    parse_mode="MarkdownV2",
                    reply_markup=abort_and_skip_keyboard(),
                )
                return

        await state.update_data(time_range=tr)
        await message.answer(
            "▶️ Enter auto\\-booking: *yes*/*no*, or press *Skip*:",
            parse_mode="MarkdownV2",
            reply_markup=id_keyboard(["yes", "no"], add_skip=True),
        )
        await state.set_state(AddWatchStates.choosing_exclusions)

    @router.message(AddWatchStates.choosing_exclusions)
    async def choose_auto_book(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await message.answer("🚫 Adding aborted.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            return
        ab = False
        if message.text and is_skip(message.text):
            ab = False  # Default auto-booking is False if skipped
        elif message.text:
            ab = validate_bool(message.text)
            if message.text and ab is None:
                await message.answer(
                    escape_markdown("❌ Invalid value. Please enter yes/no or press *Skip*."),
                    parse_mode="MarkdownV2",
                    reply_markup=id_keyboard(["yes", "no"], add_skip=True),
                )
                return

        await state.update_data(auto_book=ab)
        await ask_with_skip(
            message,
            "exclusions",
            "TYPE:ID, e.g. doctor:123,345;clinic:777,888;[...]",
        )
        await state.set_state(AddWatchStates.choosing_type)

    @router.message(AddWatchStates.choosing_type)
    async def choose_exclusions(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await message.answer("🚫 Adding aborted.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            return
        excl = None
        if message.text and is_skip(message.text):
            excl = None
        else:
            excl = validate_exclusions(message.text)
            if message.text and excl is None:
                await message.answer(
                    "❌ Invalid exclusions format. Please enter as doctor:123,345;clinic:777,888 or press *Skip*.",
                    parse_mode="MarkdownV2",
                    reply_markup=abort_and_skip_keyboard(),
                )
                return
            if excl and len(excl) > 1000:
                await message.answer(
                    "❌ Exclusions too long. Limit to 1000 characters or press *Skip*.",
                    parse_mode="MarkdownV2",
                    reply_markup=abort_and_skip_keyboard(),
                )
                return

        await state.update_data(exclusions=excl)
        await message.answer(
            "▶️ Enter type: *Standard* or *Diagnostic Procedure*:",
            parse_mode="MarkdownV2",
            reply_markup=id_keyboard(["Standard", "Diagnostic Procedure"], add_skip=True),
        )
        await state.set_state(AddWatchStates.confirming)

    @router.message(AddWatchStates.confirming)
    async def choose_type_and_confirm(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await message.answer("🚫 Adding aborted.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            return
        type_val = None
        if message.text and is_skip(message.text):
            type_val = "Standard"  # Default type if skipped
        elif message.text:
            t = message.text.strip().lower()
            if t in ["standard", "diagnostic procedure"]:
                type_val = t.title()
            else:
                await message.answer(
                    "❌ Invalid type. Please enter Standard or Diagnostic Procedure or press *Skip*.",
                    parse_mode="MarkdownV2",
                    reply_markup=id_keyboard(["Standard", "Diagnostic Procedure"], add_skip=True),
                )
                return

        await state.update_data(type=type_val)
        data = await state.get_data()
        # Compose watch details summary
        details = [
            f"Region:\t\t{data.get('region')}",
            f"City:\t\t\t{data.get('city')}",
            f"Specialty:\t\t{data.get('specialty')}",
            f"Doctor:\t\t{data.get('doctor')}",
            f"Clinic:\t\t{data.get('clinic')}",
            f"Start date:\t\t{data.get('start_date')}",
            f"End date:\t\t{data.get('end_date')}",
            f"Time range:\t\t{data.get('time_range')}",
            f"Auto-book:\t\t{data.get('auto_book')}",
            f"Exclusions:\t\t{data.get('exclusions')}",
            f"Type:\t\t\t{data.get('type')}",
            f"Account:\t\t{data.get('account', 'default')}",
        ]
        sanitized_data = "\n".join(["❇️ Watch to be added:"] + details)
        log.info("⨂ Watch to be added:")
        for detail in details:
            log.info(f"  {detail}")

        await message.answer(sanitized_data)
        try:
            watch_service.add_watch(
                region=data.get("region"),
                city=data.get("city"),
                specialty=data.get("specialty"),
                doctor_id=data.get("doctor"),
                clinic_id=data.get("clinic"),
                start_date=data.get("start_date"),
                end_date=data.get("end_date"),
                time_range=data.get("time_range"),
                auto_book=data.get("auto_book"),
                exclusions=data.get("exclusions"),
                type=data.get("type"),
                account=data.get("account", "default"),
            )
            await message.answer("✅ Watch added successfully!", reply_markup=ReplyKeyboardRemove())
        except Exception as e:
            await message.answer(f"❌ Error adding watch: {e}")

        await state.clear()
        log.info(f"↩ Finished command: {command_name}")
        return

    dispatcher.include_router(router)
    return router
