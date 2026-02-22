import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from handlers import user, admin, correction
from middlewares.auth import VerificationMiddleware
from middlewares.logging_mw import LoggingMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # LoggingMiddleware — первым (до проверки верификации)
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())

    # VerificationMiddleware — вторым (блокирует неверифицированных)
    dp.message.middleware(VerificationMiddleware())
    dp.callback_query.middleware(VerificationMiddleware())

    dp.include_router(user.router)
    dp.include_router(admin.router)
    dp.include_router(correction.router)

    logger.info("✅ Бот запущен и принимает сообщения")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
