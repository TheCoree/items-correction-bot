"""
Обработчики для администраторов.
Подтверждение и отклонение заявок на верификацию.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery

from db.users import set_status, get_user, UserStatus

router = Router()


@router.callback_query(F.data.startswith("verify:"))
async def handle_verification(callback: CallbackQuery):
    """
    Обрабатывает нажатия кнопок ✅ Подтвердить / ❌ Отклонить.
    callback.data формат: verify:{action}:{user_id}
    """
    _, action, user_id_str = callback.data.split(":")
    user_id = int(user_id_str)

    user_data = await get_user(user_id)
    full_name = user_data.get("full_name", "Пользователь") if user_data else "Пользователь"

    if action == "approve":
        await set_status(user_id, UserStatus.APPROVED)

        # Уведомляем пользователя
        await callback.bot.send_message(
            chat_id=user_id,
            text=(
                "✅ <b>Ваш аккаунт верифицирован!</b>\n\n"
                "Теперь вы можете пользоваться ботом.\n"
                "Нажмите /start для начала работы."
            ),
        )

        # Обновляем сообщение в админ-чате
        await callback.message.edit_text(
            callback.message.html_text + f"\n\n✅ <b>Подтверждён</b> администратором @{callback.from_user.username or callback.from_user.full_name}"
        )

    elif action == "reject":
        await set_status(user_id, UserStatus.REJECTED)

        # Уведомляем пользователя
        await callback.bot.send_message(
            chat_id=user_id,
            text=(
                "❌ <b>Ваша заявка на верификацию отклонена.</b>\n\n"
                "Если вы считаете, что это произошло по ошибке — обратитесь к администратору."
            ),
        )

        # Обновляем сообщение в админ-чате
        await callback.message.edit_text(
            callback.message.html_text + f"\n\n❌ <b>Отклонён</b> администратором @{callback.from_user.username or callback.from_user.full_name}"
        )

    await callback.answer()
