"""/whitelist add|del|list — admin-only."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy import select

from bot.texts import ACCESS_DENIED_ADMIN
from core.db.models import User
from core.db.session import SessionLocal

router = Router(name="whitelist")

USAGE = (
    "Использование:\n"
    "`/whitelist add <tg_id>` — добавить\n"
    "`/whitelist del <tg_id>` — удалить (деактивировать)\n"
    "`/whitelist list` — список активных"
)


@router.message(Command("whitelist"))
async def cmd_whitelist(message: Message, command: CommandObject, user: User) -> None:
    if not user.is_admin:
        await message.answer(ACCESS_DENIED_ADMIN)
        return

    args = (command.args or "").split()
    if not args:
        await message.answer(USAGE, parse_mode="Markdown")
        return

    action = args[0].lower()

    if action == "list":
        async with SessionLocal() as session:
            users = (
                (
                    await session.execute(
                        select(User).where(User.is_active.is_(True)).order_by(User.id)
                    )
                )
                .scalars()
                .all()
            )
        if not users:
            await message.answer("Список пуст.")
            return
        lines = [
            f"{u.id}. tg_id=`{u.tg_id}` @{u.username or '—'}{' 👑' if u.is_admin else ''}"
            for u in users
        ]
        await message.answer(
            "👥 *Whitelist*\n\n" + "\n".join(lines), parse_mode="Markdown"
        )
        return

    if action in ("add", "del") and len(args) >= 2:
        try:
            target_tg_id = int(args[1])
        except ValueError:
            await message.answer("⚠ tg_id должен быть числом.")
            return

        async with SessionLocal() as session:
            target = (
                await session.execute(select(User).where(User.tg_id == target_tg_id))
            ).scalar_one_or_none()

            if action == "add":
                if target is None:
                    session.add(User(tg_id=target_tg_id, is_active=True))
                    await session.commit()
                    await message.answer(
                        f"✅ Пользователь `{target_tg_id}` добавлен.\n\nПусть напишет боту /start.",
                        parse_mode="Markdown",
                    )
                elif not target.is_active:
                    target.is_active = True
                    await session.commit()
                    await message.answer(
                        f"✅ Пользователь `{target_tg_id}` снова активен.",
                        parse_mode="Markdown",
                    )
                else:
                    await message.answer(
                        f"ℹ Пользователь `{target_tg_id}` уже в списке.",
                        parse_mode="Markdown",
                    )
                return

            # del
            if target is None or not target.is_active:
                await message.answer(
                    f"ℹ Пользователь `{target_tg_id}` не в списке.",
                    parse_mode="Markdown",
                )
                return
            if target.is_admin:
                await message.answer("⛔ Нельзя удалить администратора.")
                return
            target.is_active = False
            await session.commit()
            await message.answer(
                f"🗑 Пользователь `{target_tg_id}` деактивирован.", parse_mode="Markdown"
            )
            return

    await message.answer(USAGE, parse_mode="Markdown")
