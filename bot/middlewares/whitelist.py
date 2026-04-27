"""Whitelist middleware: only users in the `users` table with is_active=True may interact.

Admin (ADMIN_TG_ID) is auto-created on first contact and always passes.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, Update
from sqlalchemy import select

from core.config import settings
from core.db.models import User
from core.db.session import SessionLocal
from core.logging import get_logger

log = get_logger("whitelist")


async def _ensure_user(tg_id: int, username: str | None) -> User | None:
    """Return User row if user exists & is_active. Auto-create admin on first contact."""
    async with SessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.tg_id == tg_id))
        ).scalar_one_or_none()

        if user is None and tg_id == settings.ADMIN_TG_ID:
            user = User(
                tg_id=tg_id,
                username=username,
                is_admin=True,
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            log.info("admin_user_created", tg_id=tg_id, username=username)
            return user

        if user is None:
            return None

        if user.is_active and user.username != username and username:
            user.username = username
            await session.commit()

        return user if user.is_active else None


class WhitelistMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Resolve incoming user
        tg_user = None
        if isinstance(event, Update):
            tg_user = (
                (event.message and event.message.from_user)
                or (event.callback_query and event.callback_query.from_user)
                or (event.inline_query and event.inline_query.from_user)
                or (event.my_chat_member and event.my_chat_member.from_user)
            )

        if tg_user is None:
            return await handler(event, data)

        user = await _ensure_user(tg_user.id, tg_user.username)

        if user is None:
            log.warning(
                "whitelist_blocked", tg_id=tg_user.id, username=tg_user.username
            )
            # Reply only to direct messages, silently ignore everything else
            if isinstance(event, Update) and event.message:
                await event.message.answer(
                    "🚫 Доступ закрыт.\n\n"
                    "Этот бот работает только для пользователей из белого списка. "
                    "Обратитесь к администратору."
                )
            return None

        # Pass user object downstream
        data["user"] = user
        return await handler(event, data)
