"""Bot entrypoint: applies migrations, configures middleware, starts polling."""

from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from alembic import command
from alembic.config import Config as AlembicConfig

from bot.handlers import common, feedback, whitelist
from bot.middlewares.ratelimit import RateLimitMiddleware
from bot.middlewares.whitelist import WhitelistMiddleware
from core.config import settings
from core.logging import get_logger, setup_logging

setup_logging()
log = get_logger("main")


def _run_migrations() -> None:
    log.info("alembic_upgrade_start")
    cfg = AlembicConfig("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", settings.alembic_database_url)
    command.upgrade(cfg, "head")
    log.info("alembic_upgrade_done")


async def main() -> None:
    _run_migrations()

    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    storage = RedisStorage(redis=redis)

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=None),
    )
    dp = Dispatcher(storage=storage)

    # Outer middlewares (run on every update)
    dp.update.outer_middleware(WhitelistMiddleware())
    dp.update.outer_middleware(RateLimitMiddleware(redis=redis))

    # Routers
    dp.include_router(common.router)
    dp.include_router(feedback.router)
    dp.include_router(whitelist.router)

    me = await bot.get_me()
    log.info("bot_started", username=me.username, id=me.id)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await redis.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("bot_stopped")
