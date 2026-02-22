"""
Middleware логирования входящих сообщений.
Выводит в консоль информацию о каждом написавшем пользователе —
для удобного добавления новых админов.
"""

import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from config import is_admin

logger = logging.getLogger("UserLog")


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user:
            role = "👑 ADMIN" if is_admin(user.id) else "👤 USER"
            username = f"@{user.username}" if user.username else "нет username"

            if isinstance(event, Message):
                text = (event.text or event.caption or "[медиа]")[:60]
                logger.info(
                    f"{role} | ID: {user.id} | {username} | "
                    f"Имя: {user.full_name!r} | Сообщение: {text!r}"
                )
            elif isinstance(event, CallbackQuery):
                logger.info(
                    f"{role} | ID: {user.id} | {username} | "
                    f"Имя: {user.full_name!r} | Callback: {event.data!r}"
                )

        return await handler(event, data)
