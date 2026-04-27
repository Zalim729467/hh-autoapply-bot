"""/feedback <text> — forward to admin."""

from __future__ import annotations

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.exc import SQLAlchemyError

from bot.texts import FEEDBACK_FAILED, FEEDBACK_THANKS, FEEDBACK_USAGE
from core.config import settings
from core.db.models import Feedback, User
from core.db.session import SessionLocal
from core.logging import get_logger

router = Router(name="feedback")
log = get_logger("feedback")


@router.message(Command("feedback"))
async def cmd_feedback(
    message: Message, command: CommandObject, user: User, bot: Bot
) -> None:
    text = (command.args or "").strip()
    if not text:
        await message.answer(FEEDBACK_USAGE, parse_mode="Markdown")
        return

    forwarded_id: int | None = None
    try:
        sent = await bot.send_message(
            settings.ADMIN_TG_ID,
            f"💬 *Feedback*\n\n"
            f"От: @{user.username or '—'} (tg_id={user.tg_id})\n\n"
            f"{text}",
            parse_mode="Markdown",
        )
        forwarded_id = sent.message_id
    except Exception as e:  # noqa: BLE001
        log.warning("feedback_forward_failed", error=str(e))
        await message.answer(FEEDBACK_FAILED)
        return

    try:
        async with SessionLocal() as session:
            session.add(
                Feedback(
                    user_id=user.id, message=text, forwarded_message_id=forwarded_id
                )
            )
            await session.commit()
    except SQLAlchemyError as e:
        log.warning("feedback_db_save_failed", error=str(e))

    await message.answer(FEEDBACK_THANKS)
