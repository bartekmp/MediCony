from aiogram import Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove

from src.bot.shared_utils import id_keyboard, is_abort
from src.bot.telegram import format_elements_as_text
from src.logger import log
from src.medicover.services.watch_service import WatchService


class RemoveWatchStates(StatesGroup):
    choosing_watch = State()


def register_remove_watch_handler(dispatcher: Dispatcher, watch_service: WatchService):
    router = Router()
    command_name = "/watch_remove"

    @router.message(Command("watch_remove"))
    async def handle_remove_watch(message: types.Message, state: FSMContext):
        log.info(f"↪ Received command: {command_name}")
        watches = await watch_service.get_all_watches()
        if not watches:
            await message.answer("⚠️ No watches found, nothing to remove.", parse_mode="MarkdownV2")
            log.info(f"↩ Finished command: {command_name}")
            return
        formatted_watches = format_elements_as_text(watches)
        await message.answer(
            f"Active watches: {len(watches)}\n" f"🗑️ Choose a watch to remove:\n{'-' * 50}\n{formatted_watches}",
        )
        watch_ids = [str(w.id) for w in watches]
        await message.answer(
            "▶️ Choose the *ID* of the watch to remove:",
            parse_mode="MarkdownV2",
            reply_markup=id_keyboard(watch_ids, add_abort=True),
        )
        await state.update_data(watches=[{"id": w.id} for w in watches])
        await state.set_state(RemoveWatchStates.choosing_watch)

    @router.message(RemoveWatchStates.choosing_watch)
    async def choose_watch_to_remove(message: types.Message, state: FSMContext):
        if message.text and is_abort(message.text):
            await message.answer("🚫 Removal aborted.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            log.info(f"↩ Aborted command: {command_name}")
            return
        data = await state.get_data()
        watches = data.get("watches", [])
        watch_id = f"{message.text}".strip()
        all_watch_ids = [str(w["id"]) for w in watches]
        if watch_id and not any(w == watch_id for w in all_watch_ids):
            await message.answer(
                "❌ Invalid watch ID. Please try again.", reply_markup=id_keyboard(all_watch_ids, add_abort=True)
            )
            return
        try:
            removed = watch_service.remove_watch(int(watch_id))
            if removed:
                log_msg = f"✅ Watch with ID {watch_id} removed successfully!"
                await message.answer(log_msg, reply_markup=ReplyKeyboardRemove())
                log.info(log_msg)
            else:
                log_msg = f"❌ Failed to remove watch with ID {watch_id}. Try again."
                await message.answer(log_msg, reply_markup=ReplyKeyboardRemove())
                log.error(log_msg)
        except Exception as e:
            await message.answer(f"❌ Error removing watch: {e}", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        log.info(f"↩ Finished command: {command_name}")

    dispatcher.include_router(router)
    return router
