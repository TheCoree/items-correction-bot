"""
Обработчики для обычных пользователей.
"""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import hbold, hcode

from db.users import get_status, upsert_user, UserStatus
from config import ADMIN_CHAT_ID, is_admin

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user

    # ── Администратор ──────────────────────────────────────────────────
    if is_admin(user.id):
        await upsert_user(user.id, {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "status": UserStatus.APPROVED.value,
        })
        await message.answer(
            f"👑 <b>Добро пожаловать, Администратор!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>{hbold(user.full_name)}</b>\n"
            f"🆔 ID: {hcode(str(user.id))}\n\n"
            f"🔓 У вас <b>полный доступ</b> ко всем функциям бота.\n"
            f"Заявки на верификацию будут приходить вам в этот чат."
        )
        return

    # ── Проверяем текущий статус ────────────────────────────────────────
    status = await get_status(user.id)

    if status == UserStatus.APPROVED:
        await message.answer(
            f"👋 Добро пожаловать, {hbold(user.full_name)}!\n"
            "Вы верифицированы и можете пользоваться ботом."
        )
        return

    if status == UserStatus.PENDING:
        await message.answer(
            "⏳ <b>Ваш аккаунт находится на стадии верификации.</b>\n\n"
            "Вам будет отправлено уведомление, как только администратор рассмотрит вашу заявку."
        )
        return

    if status == UserStatus.REJECTED:
        await message.answer(
            "❌ <b>Ваша заявка была отклонена.</b>\n\n"
            "Если вы считаете, что это ошибка — обратитесь к администратору."
        )
        return

    # ── Новый пользователь — создаём заявку ────────────────────────────
    await upsert_user(user.id, {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "status": UserStatus.PENDING.value,
    })

    await message.answer(
        "⏳ <b>Ваш аккаунт находится на стадии верификации.</b>\n\n"
        "Вам будет отправлено уведомление, как только администратор рассмотрит вашу заявку.\n\n"
        "Пожалуйста, ожидайте."
    )

    # ── Уведомление всем администраторам с inline-кнопками ──────────────
    admin_targets = set()
    if ADMIN_CHAT_ID:
        admin_targets.add(ADMIN_CHAT_ID)
    from config import ADMIN_IDS
    admin_targets.update(ADMIN_IDS)

    if admin_targets:
        username_str = f"@{user.username}" if user.username else "<i>нет username</i>"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить",
                    callback_data=f"verify:approve:{user.id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"verify:reject:{user.id}"
                ),
            ]
        ])
        
        text = (
            "🔔 <b>Новая заявка на верификацию</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Имя: {hbold(user.full_name)}\n"
            f"🆔 ID: {hcode(str(user.id))}\n"
            f"📎 Username: {username_str}"
        )

        for target_id in admin_targets:
            try:
                await message.bot.send_message(
                    chat_id=target_id,
                    text=text,
                    reply_markup=keyboard,
                )
            except Exception as e:
                # В логах можно зафиксировать, что одному из админов не ушло
                pass
