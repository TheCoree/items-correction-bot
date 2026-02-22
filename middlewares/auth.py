"""
Middleware верификации.
Блокирует доступ к боту для неверифицированных пользователей,
кроме команды /start и администраторов.
"""

from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from db.users import get_status, UserStatus
from config import is_admin

# Команды, доступные без верификации
ALLOWED_COMMANDS = {"/start"}


class VerificationMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        # ── Администраторы всегда проходят ─────────────────────────────
        if is_admin(user.id):
            return await handler(event, data)

        # ── Пропускаем разрешённые команды (/start) ────────────────────
        if isinstance(event, Message):
            text = event.text or ""
            command = text.split()[0] if text.startswith("/") else None
            if command and command.split("@")[0] in ALLOWED_COMMANDS:
                return await handler(event, data)

        # ── Проверяем статус пользователя ──────────────────────────────
        status = await get_status(user.id)

        if status == UserStatus.APPROVED:
            return await handler(event, data)

        # Для CallbackQuery — всплывающее уведомление
        if isinstance(event, CallbackQuery):
            if status == UserStatus.PENDING:
                await event.answer("⏳ Ваш аккаунт ещё не верифицирован.", show_alert=True)
            elif status == UserStatus.REJECTED:
                await event.answer("❌ Ваша заявка отклонена.", show_alert=True)
            else:
                await event.answer("⚠️ Отправьте /start для начала работы.", show_alert=True)
            return

        # Для Message — текстовый ответ
        if isinstance(event, Message):
            if status == UserStatus.PENDING:
                await event.answer(
                    "⏳ <b>Ваш аккаунт ещё не верифицирован.</b>\n"
                    "Ожидайте уведомления от бота."
                )
            elif status == UserStatus.REJECTED:
                await event.answer(
                    "❌ <b>Ваша заявка была отклонена.</b>\n"
                    "Обратитесь к администратору."
                )
            else:
                await event.answer(
                    "⚠️ Для доступа необходима верификация.\n"
                    "Отправьте /start чтобы подать заявку."
                )
