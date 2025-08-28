from collections.abc import Sequence
from typing import Any, Optional

from aiogram import Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove

from src.bot.shared_utils import (
    abort_and_skip_keyboard,
    ask_with_skip,
    escape_markdown,
    format_current_value,
    id_keyboard,
    is_abort,
    is_skip,
)
from src.bot.telegram import format_elements_as_text
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
from src.medicover.watch import Watch, WatchTimeRange, flatten_exclusions


def get_watch_by_id(watches: Sequence[Watch], id_: str) -> Watch | None:
    for w in watches:
        if str(w.id) == id_:
            return w
    return None


def get_changed_fields(old: Watch, new: dict) -> dict[str, Any]:
    """
    Compare old Watch object and new values dict.
    For IdValue fields (clinic, doctor), compare their .id attribute if present.
    For WatchTimeRange, compare as string.
    """

    changed = {}
    for k, v in new.items():
        if v is None:
            continue
        # Handle IdValue fields
        if k == "clinic_id" and hasattr(old, "clinic"):
            old_id = getattr(old.clinic, "id", None) if old.clinic else None
            if v != old_id:
                changed[k] = v
        elif k == "doctor_id" and hasattr(old, "doctor"):
            old_id = getattr(old.doctor, "id", None) if old.doctor else None
            if v != old_id:
                changed[k] = v
        elif k == "time_range":
            old_val = getattr(old, k, None)
            # Compare as string if either is WatchTimeRange or str
            old_str = str(old_val) if isinstance(old_val, (WatchTimeRange, str)) else old_val
            new_str = str(v) if isinstance(v, (WatchTimeRange, str)) else v
            if old_str != new_str:
                changed[k] = v
        else:
            old_val = getattr(old, k, None)
            if v != old_val:
                changed[k] = v
    return changed


class EditWatchStates(StatesGroup):
    choosing_watch = State()
    editing_city = State()
    editing_clinic = State()
    editing_start_date = State()
    editing_end_date = State()
    editing_time_range = State()
    editing_exclusions = State()
    editing_auto_book = State()
    confirming = State()


def register_edit_watch_handler(dispatcher: Dispatcher, watch_service: WatchService):
    router = Router()
    command_name = "/watch_edit"

    @router.message(Command("watch_edit"))
    async def handle_edit_watch(message: types.Message, state: FSMContext):
        log.info(f"↪ Received command: {command_name}")
        watches = await watch_service.get_all_watches()
        if not watches:
            await message.answer("⚠️ *No watches found, nothing to edit*")
            log.info(f"↩ Finished command: {command_name}")
            return

        await message.answer(f"📋 Choose a watch to edit:\n{'-' * 50}\n{format_elements_as_text(watches)}")
        await state.update_data(watches=watches)
        watch_ids = [w.id for w in watches]
        await message.answer(
            "▶️ Choose the *ID* of the watch to edit:", parse_mode="MarkdownV2", reply_markup=id_keyboard(watch_ids)
        )
        await state.set_state(EditWatchStates.choosing_watch)

    @router.message(EditWatchStates.choosing_watch)
    async def choose_watch(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await message.answer("🚫 Editing aborted. All changes discarded.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            return

        watches = (await state.get_data()).get("watches", [])
        watch = get_watch_by_id(watches, f"{message.text}".strip())
        if not watch:
            await message.answer("❌ *Invalid watch ID*\nPlease try again", parse_mode="MarkdownV2")
            return

        log.info(f"⨂ Selected watch no. {watch.id} for editing")
        await state.update_data(watch=watch)
        await ask_with_skip(message, "city", None, getattr(watch, "city", ""))
        await state.set_state(EditWatchStates.editing_city)

    @router.message(EditWatchStates.editing_city)
    async def edit_city(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await message.answer("🚫 Editing aborted. All changes discarded.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            return

        city = None if message.text and is_skip(message.text) else validate_str(message.text)
        await state.update_data(city=city)
        watch = (await state.get_data()).get("watch")
        if not watch:
            await message.answer("❌ *No watch selected*\n*Please try again*", parse_mode="MarkdownV2")
            await state.clear()
            return

        clinics = await watch_service.list_available_filters(
            "clinics", region=watch.region.id, specialty=watch.specialty[0].id
        )
        if not clinics:
            await message.answer("❌ *Couldn't get clinic IDs*", parse_mode="MarkdownV2")
            await state.clear()
            return

        if available_clinics := "".join([f"  *{c['id']}* : {escape_markdown(c['value'])}\n" for c in clinics]):
            await message.answer("💡 Available clinics in given region:\n" + available_clinics, parse_mode="MarkdownV2")

        clinic_ids = [c["id"] for c in clinics]
        await message.answer(
            f"Current clinic ID: *{watch.clinic.id if watch.clinic else 'any'}*\n"
            "▶️ Enter new clinic ID or press *Skip*:",
            parse_mode="MarkdownV2",
            reply_markup=id_keyboard(clinic_ids, add_skip=True),
        )
        await state.set_state(EditWatchStates.editing_clinic)

    @router.message(EditWatchStates.editing_clinic)
    async def edit_clinic(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await message.answer("🚫 Editing aborted. All changes discarded.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            return

        if message.text and is_skip(message.text):
            clinic_id = None
        else:
            clinic = f"{message.text}".strip()
            clinic_id = validate_int(clinic) if clinic else None
            if clinic and clinic_id is None:
                await message.answer(
                    "❌ *Invalid clinic ID*\nPlease enter a valid integer or press *Skip*:", parse_mode="MarkdownV2"
                )
                return

        watch = (await state.get_data()).get("watch")
        await state.update_data(clinic=clinic_id)
        await ask_with_skip(message, "start date", "YYYY-MM-DD", getattr(watch, "start_date", ""))
        await state.set_state(EditWatchStates.editing_start_date)

    @router.message(EditWatchStates.editing_start_date)
    async def edit_start_date(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await message.answer("🚫 Editing aborted. All changes discarded.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            return

        start_date = f"{message.text}".strip()
        if start_date and is_skip(start_date):
            date_val = None
        else:
            date_val = validate_date(start_date) if start_date else None

            if start_date and date_val is None:
                await message.answer(
                    "❌ *Invalid date format*\nPlease enter as *YYYY\\-MM\\-DD* or press *Skip*:",
                    parse_mode="MarkdownV2",
                )
                return

            if date_val and validate_date_not_in_past(date_val.isoformat()) is None:
                await message.answer(
                    "❌ *Date cannot be in the past*\nPlease enter a valid date or press *Skip*:",
                    parse_mode="MarkdownV2",
                )
                return

        watch = (await state.get_data()).get("watch")
        await state.update_data(start_date=date_val)
        await ask_with_skip(message, "end date", "YYYY-MM-DD", getattr(watch, "end_date", ""))
        await state.set_state(EditWatchStates.editing_end_date)

    @router.message(EditWatchStates.editing_end_date)
    async def edit_end_date(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await message.answer("🚫 Editing aborted. All changes discarded.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            return

        start_date = (await state.get_data()).get("start_date")
        end_date = f"{message.text}".strip()
        if end_date and is_skip(end_date):
            date_val = None
        else:
            date_val = validate_date(end_date) if end_date else None

            if end_date and date_val is None:
                await message.answer(
                    "❌ *Invalid date format*\nPlease enter as *YYYY\\-MM\\-DD*:",
                    parse_mode="MarkdownV2",
                )
                return

            if date_val and start_date and not validate_date_difference(str(start_date), date_val.isoformat()):
                await message.answer(
                    "❌ *End date cannot be earlier than start date*\nPlease enter a valid end date or press *Skip*:",
                    parse_mode="MarkdownV2",
                )
                return

            if date_val and validate_date_not_in_past(date_val.isoformat()) is None:
                await message.answer(
                    "❌ *End date cannot be in the past*\nPlease enter a valid end date or press *Skip*:",
                    parse_mode="MarkdownV2",
                )
                return

        watch = (await state.get_data()).get("watch")
        await state.update_data(end_date=date_val)
        await ask_with_skip(
            message,
            "time range",
            "HH:MM-HH:MM, or just HH:MM for endless (up to 23:59:59)",
            getattr(watch, "time_range", None),
        )
        await state.set_state(EditWatchStates.editing_time_range)

    @router.message(EditWatchStates.editing_time_range)
    async def edit_time_range(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await message.answer("🚫 Editing aborted. All changes discarded.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            return

        tr = f"{message.text}".strip()
        if tr and is_skip(tr):
            tr_val = None
        else:
            tr_val = validate_time_range(tr) if tr else None

            if tr and tr_val is None:
                await message.answer(
                    "❌ *Invalid time range format*\nPlease enter as *HH:MM:SS\\[\\-HH:MM:SS\\]* or press *Skip*:",
                    reply_markup=abort_and_skip_keyboard(),
                    parse_mode="MarkdownV2",
                )
                return

        watch = (await state.get_data()).get("watch")
        await state.update_data(time_range=tr_val)
        watch_exclusions = getattr(watch, "exclusions", None)
        flat_exclusions = flatten_exclusions(watch_exclusions) if watch_exclusions else None
        await ask_with_skip(message, "exclusions", "TYPE:ID, e.g. doctor:123,345;clinic:777,888;[...]", flat_exclusions)
        await state.set_state(EditWatchStates.editing_exclusions)

    @router.message(EditWatchStates.editing_exclusions)
    async def edit_exclusions(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await message.answer("🚫 Editing aborted. All changes discarded.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            return

        excl = f"{message.text}".strip()
        if excl and is_skip(excl):
            excl_val = None
        else:
            excl_val = validate_exclusions(excl) if excl else None
            if excl and excl_val is None:
                await message.answer(
                    "❌ *Invalid exclusions format*\nPlease enter as *doctor:123,345;clinic:777,888* or press *Skip*:",
                    parse_mode="MarkdownV2",
                )
                return
            if excl_val and len(excl_val) > 1000:
                await message.answer(
                    "❌ *Exclusions too long*\nLimit to 1000 characters or press *Skip*:",
                    parse_mode="MarkdownV2",
                )
                return

        watch = (await state.get_data()).get("watch")
        await state.update_data(exclude=excl_val)
        await message.answer(
            f"{format_current_value('auto-booking', 'yes' if getattr(watch, 'auto_book', False) else 'no')}\n"
            + "▶️ Enter new auto\\-booking: *yes*/*no*, or press *Skip*:",
            parse_mode="MarkdownV2",
            reply_markup=id_keyboard(["yes", "no"], add_skip=True),
        )
        await state.set_state(EditWatchStates.editing_auto_book)

    @router.message(EditWatchStates.editing_auto_book)
    async def edit_auto_book(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await message.answer("🚫 Editing aborted. All changes discarded.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            return

        ab = f"{message.text}".strip()
        if ab and is_skip(ab.lower()):
            ab_val = None
        else:
            ab_val = validate_bool(ab) if ab else None
            if ab and ab_val is None:
                await message.answer(
                    "❌ *Invalid value*\nPlease enter *yes*/*no* or press *Skip*:",
                    parse_mode="MarkdownV2",
                    reply_markup=id_keyboard(["yes", "no"], add_skip=True),
                )
                return

        await state.update_data(auto_book=ab_val)
        await message.answer("⌛ Saving changes...", reply_markup=ReplyKeyboardRemove())
        await state.set_state(EditWatchStates.confirming)

        # Perform the DB entry update
        data = await state.get_data()
        try:
            old_watch: Optional[Watch] = data.get("watch")
            if not old_watch:
                await message.answer("❌ Error: Watch not found")
                await state.clear()
                return

            update_kwargs = {
                "city": data.get("city"),
                "clinic_id": data.get("clinic"),
                "start_date": data.get("start_date"),
                "end_date": data.get("end_date"),
                "time_range": data.get("time_range"),
                "exclusions": data.get("exclude"),
                "auto_book": data.get("auto_book"),
            }
            changed = get_changed_fields(old_watch, update_kwargs)  # type: ignore
            if not changed:
                await message.answer("⚠️ No changes provided and nothing was updated")
                await state.clear()
                return

            if watch_service.update_watch(
                old_watch,
                city=data.get("city"),
                clinic_id=data.get("clinic"),
                start_date=data.get("start_date"),
                end_date=data.get("end_date"),
                time_range=data.get("time_range"),
                exclusions=data.get("exclude"),
                auto_book=data.get("auto_book"),
            ):
                changed_fields = "\n".join([f"{k}:\t\t\t{v}" for k, v in changed.items()])
                log_msg = f"✅ Watch no. {old_watch.id} updated successfully\n\nChanged fields:\n\n{changed_fields}"
                await message.answer(log_msg)

                for log_msg in log_msg.splitlines():
                    log.info(log_msg)
            else:
                await message.answer("❌ Error updating watch, it may not exist or the update failed")
                log.error(f"Failed to update watch no. {old_watch.id} with data: {update_kwargs}")
                return

        except Exception as e:
            await message.answer(f"❌ Error updating watch: {e}")
        await state.clear()
        log.info(f"↩ Finished command: {command_name}")

    dispatcher.include_router(router)
    return router
