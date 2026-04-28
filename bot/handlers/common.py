"""/start, /help, /menu, /cancel."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards.main_menu import main_menu_kb
from bot.texts import (
    CANCELED,
    HELP_TEXT,
    MENU_OPENED,
    START_TEXT_ADMIN,
    START_TEXT_USER,
)
from core.db.models import User

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message, user: User) -> None:
    if user.is_admin:
        text = START_TEXT_ADMIN
    else:
        name = message.from_user.first_name if message.from_user else "друг"
        text = START_TEXT_USER.format(name=name)
    await message.answer(text, parse_mode="Markdown", reply_markup=main_menu_kb())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode="Markdown", reply_markup=main_menu_kb())


@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    await message.answer(MENU_OPENED, reply_markup=main_menu_kb())


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(CANCELED, reply_markup=main_menu_kb())
