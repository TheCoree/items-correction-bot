"""
Хранилище пользователей.

Статусы (UserStatus):
  - pending    — подал заявку, ждёт верификации
  - approved   — верифицирован, может пользоваться ботом
  - rejected   — отклонён администратором
"""

import json
import os
import aiofiles
from enum import Enum
from typing import Optional

USERS_FILE = os.path.join(os.path.dirname(__file__), "..", "users.json")


class UserStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


async def _load() -> dict:
    if not os.path.exists(USERS_FILE):
        return {}
    async with aiofiles.open(USERS_FILE, "r", encoding="utf-8") as f:
        content = await f.read()
        return json.loads(content) if content.strip() else {}


async def _save(data: dict) -> None:
    async with aiofiles.open(USERS_FILE, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, ensure_ascii=False, indent=2))


async def get_user(user_id: int) -> Optional[dict]:
    data = await _load()
    return data.get(str(user_id))


async def upsert_user(user_id: int, payload: dict) -> None:
    data = await _load()
    key = str(user_id)
    if key not in data:
        data[key] = {}
    data[key].update(payload)
    await _save(data)


async def set_status(user_id: int, status: UserStatus) -> None:
    await upsert_user(user_id, {"status": status.value})


async def get_status(user_id: int) -> Optional[UserStatus]:
    user = await get_user(user_id)
    if not user:
        return None
    return UserStatus(user["status"])
