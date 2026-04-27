"""/start, /help, /menu, /cancel."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.texts import (
    CANCELED,
    HELP_TEXT,
    MENU_PLACEHOLDER,
    START_TEXT_ADMIN,
    START_TEXT_USER,
)
from core.db.models import User

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message, user: User) -> None:
    if user.is_admin:
        await message.answer(START_TEXT_ADMIN, parse_mode="Markdown")
    else:
        name = message.from_user.first_name if message.from_user else "друг"
        await message.answer(START_TEXT_USER.format(name=name), parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode="Markdown")


@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    await message.answer(MENU_PLACEHOLDER, parse_mode="Markdown")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(CANCELED)


@router.message(F.text == "❓ Помощь")
async def kb_help(message: Message) -> None:
    await cmd_help(message)
