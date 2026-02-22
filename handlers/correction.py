"""
Обработчик для заявок на корректировку товаров.

Верифицированный пользователь отправляет фото(+текст) → бот делает
POST /correction-orders на бэкенд с multipart/form-data.
Поддерживается как одиночное фото, так и альбом (media_group).
"""

import asyncio
import io
import logging
from collections import defaultdict

import aiohttp
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

from config import BACKEND_URL, BOT_SECRET_KEY

router = Router()
logger = logging.getLogger(__name__)

# ── Состояния FSM ────────────────────────────────────────────────────────────
class CorrectionState(StatesGroup):
    waiting_for_replacement = State()  # Ждем новую версию заявки после ввода ID

# ── Буфер для сборки media_group ─────────────────────────────────────────────
# ... (existing buffer code)
_media_group_buffer: dict[str, list[Message]] = defaultdict(list)
_media_group_tasks: dict[str, asyncio.TimerHandle] = {}


async def _send_order(bot: Bot, messages: list[Message], replace_id: int = None, status_msg: Message = None):
    """Собирает данные из сообщений и отправляет POST на бэкенд."""
    first = messages[0]
    user = first.from_user

    # Описание берём из подписи первого фото (или любого с caption)
    description = next(
        (m.caption for m in messages if m.caption),
        None,
    )

    # Скачиваем все фото через Telegram API
    photo_bytes: list[tuple[str, bytes]] = []
    for msg in messages:
        if msg.photo:
            file_id = msg.photo[-1].file_id
            tg_file = await bot.get_file(file_id)
            buf = io.BytesIO()
            await bot.download_file(tg_file.file_path, buf)
            filename = f"{file_id}.jpg"
            photo_bytes.append((filename, buf.getvalue()))

    # Если статусное сообщение не передано, создаем его
    if not status_msg:
        status_msg = await first.answer("📤 <i>Отправляю заявку...</i>")

    # Отправляем multipart POST
    url = f"{BACKEND_URL}/correction-orders/"
    headers = {"X-Bot-Secret": BOT_SECRET_KEY}

    try:
        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field("telegram_user_id", str(user.id))
            form.add_field("telegram_chat_id", str(first.chat.id))
            if user.username:
                form.add_field("telegram_username", user.username)
            if user.full_name:
                form.add_field("telegram_full_name", user.full_name)
            if description:
                form.add_field("description", description)
            if replace_id:
                form.add_field("replace_order_id", str(replace_id))
            if first.message_id:
                form.add_field("user_message_id", str(first.message_id))

            for filename, data in photo_bytes:
                form.add_field(
                    "photos",
                    data,
                    filename=filename,
                    content_type="image/jpeg",
                )

            async with session.post(url, data=form, headers=headers) as resp:
                if resp.status == 201:
                    order = await resp.json()
                    status_text = "успешно создана" if not replace_id else f"обновлена (номер #{replace_id} сохранен)"
                    await status_msg.edit_text(
                        f"✅ <b>Заявка #{order['id']} {status_text}!</b>\n"
                        f"📋 Описание: {description or '<i>не указано</i>'}\n"
                        f"⏳ Заявка в работе."
                    )
                else:
                    body = await resp.text()
                    logger.error("Backend error %s: %s", resp.status, body)
                    await status_msg.edit_text(f"❌ <b>Ошибка сервера ({resp.status}).</b>\n\nПожалуйста, попробуйте позже.")
    except Exception as exc:
        logger.exception("Error sending order: %s", exc)
        try:
            await status_msg.edit_text("❌ <b>Произошла ошибка при отправке.</b>\n\nПроверьте соединение и попробуйте снова.")
        except:
            await first.answer("❌ Произошла ошибка при отправке.")


# ── Обработка ID для замены ──────────────────────────────────────────────────
@router.message(F.text.regexp(r"^\d+$"))
async def handle_order_id_for_replacement(message: Message, state: FSMContext):
    order_id = int(message.text)
    await state.update_data(replace_id=order_id)
    await state.set_state(CorrectionState.waiting_for_replacement)
    await message.answer(
        f"🔄 <b>Вы указали ID заявки #{order_id} для обновления.</b>\n"
        "Теперь отправьте новые фотографии и описание (одним сообщением или альбомом). "
        "Данные в системе будут обновлены."
    )


# ── Обработчики фото ──────────────────────────────────────────────────────────
@router.message(F.photo & ~F.media_group_id)
async def handle_single_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    replace_id = data.get("replace_id")
    
    status_msg = await message.answer("📤 <i>Отправляю заявку...</i>")
    await _send_order(message.bot, [message], replace_id=replace_id, status_msg=status_msg)
    await state.clear()


@router.message(F.photo & F.media_group_id)
async def handle_album_photo(message: Message, state: FSMContext):
    group_id = message.media_group_id
    _media_group_buffer[group_id].append(message)

    if group_id in _media_group_tasks:
        return

    async def _flush():
        await asyncio.sleep(0.5)
        messages = _media_group_buffer.pop(group_id, [])
        _media_group_tasks.pop(group_id, None)
        if messages:
            data = await state.get_data()
            replace_id = data.get("replace_id")
            status_msg = await messages[0].answer("📤 <i>Отправляю заявку...</i>")
            await _send_order(messages[0].bot, messages, replace_id=replace_id, status_msg=status_msg)
            await state.clear()

    _media_group_tasks[group_id] = asyncio.ensure_future(_flush())


@router.callback_query(F.data.startswith("user_confirm_"))
async def process_user_confirm(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[-1])
    url = f"{BACKEND_URL}/correction-orders/{order_id}/user-confirm"
    headers = {"X-Bot-Secret": BOT_SECRET_KEY}

    # Сразу отвечаем, чтобы убрать спиннер, но даем понять, что процесс идет
    await callback.answer("⏳ Заявка в работе...")
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.post(url, headers=headers) as resp:
                if resp.status == 200:
                    order_data = await resp.json()
                    await callback.message.edit_reply_markup(reply_markup=None)
                    reply_params = {}
                    if order_data.get("user_message_id"):
                        reply_params = {"reply_to_message_id": order_data["user_message_id"]}
                    
                    await callback.message.reply(
                        f"✅ <b>Заявка #{order_id} выполнена успешно!</b>",
                        **reply_params
                    )
                else:
                    body = await resp.json()
                    detail = body.get("detail", "Ошибка сервера")
                    await callback.message.reply(f"❌ <b>Ошибка:</b> {detail}")
    except Exception as e:
        logger.error("Callback error: %s", e)
        await callback.message.reply("❌ Ошибка связи с сервером. Попробуйте позже.")


# ── Обработка "Изменить" от пользователя ──────────────────────────────────────
@router.callback_query(F.data.startswith("user_edit_"))
async def handle_user_edit(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[-1])
    await state.update_data(replace_id=order_id)
    await state.set_state(CorrectionState.waiting_for_replacement)
    
    await callback.answer()
    await callback.message.reply(
        f"⚠️ <b>ключен режим редактирования заявки #{order_id}.</b>\n\n"
        "‼️ Пожалуйста, пересоздайте заявку с учетом дополнительной информации."
    )
