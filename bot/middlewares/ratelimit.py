"""Per-user rate limit middleware (Redis-backed).

Drops updates that come faster than `RATE_LIMIT_PER_SEC` per Telegram user.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from redis.asyncio import Redis

from core.config import settings
from core.logging import get_logger

log = get_logger("ratelimit")


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, redis: Redis, per_sec: float | None = None) -> None:
        self.redis = redis
        self.window_ms = int(1000 / (per_sec or settings.RATE_LIMIT_PER_SEC))

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = None
        if isinstance(event, Update):
            tg_user = (event.message and event.message.from_user) or (
                event.callback_query and event.callback_query.from_user
            )

        if tg_user is None:
            return await handler(event, data)

        # Admin is exempt
        if tg_user.id == settings.ADMIN_TG_ID:
            return await handler(event, data)

        key = f"rl:{tg_user.id}"
        # SET key 1 PX <window> NX → returns True only if it was set fresh
        ok = await self.redis.set(key, 1, px=self.window_ms, nx=True)
        if not ok:
            log.debug("rate_limited", tg_id=tg_user.id)
            return None

        return await handler(event, data)
