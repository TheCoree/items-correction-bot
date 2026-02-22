"""
Централизованная конфигурация.
Читает переменные из .env один раз при старте.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота от BotFather
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

# ID чата / группы, куда приходят заявки на верификацию
# Для личного чата — это твой user ID (number, e.g. 123456789)
# Для группы — отрицательный ID (e.g. -1001234567890)
ADMIN_CHAT_ID: int = int(os.getenv("ADMIN_CHAT_ID", "0"))

# Список ID администраторов через запятую (например: 123456789,987654321)
# Эти пользователи автоматически имеют доступ к боту без верификации
_admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: set[int] = {
    int(x.strip())
    for x in _admin_ids_raw.split(",")
    if x.strip().isdigit()
}

# URL бэкенда Pulse TTM
BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

# Секретный ключ для подписи запросов к API (должен совпадать с backend .env)
BOT_SECRET_KEY: str = os.getenv("BOT_SECRET_KEY", "")


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором."""
    return user_id in ADMIN_IDS


if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в .env файле")
