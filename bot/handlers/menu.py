"""Main-menu navigation: button handlers + slash commands /run /stop /status /dry."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot import texts
from bot.keyboards.main_menu import (
    BTN_ACCOUNTS,
    BTN_ATTENTION,
    BTN_BACK,
    BTN_DRY,
    BTN_HELP,
    BTN_MINIAPP,
    BTN_RESUMES,
    BTN_RUN,
    BTN_SCHEDULE,
    BTN_SETTINGS,
    BTN_STATS,
    BTN_STOP,
    back_only_kb,
    main_menu_kb,
)

router = Router(name="menu")


# --- Generic helpers ---


async def _show_screen(message: Message, text: str) -> None:
    """Show a stub screen with a 'back to menu' keyboard."""
    await message.answer(text, parse_mode="Markdown", reply_markup=back_only_kb())


# --- Back ---


@router.message(F.text == BTN_BACK)
async def back_to_menu(message: Message) -> None:
    await message.answer(texts.BACK_TO_MENU, reply_markup=main_menu_kb())


# --- Menu buttons (§5.1) ---


@router.message(F.text == BTN_RUN)
@router.message(Command("run"))
async def on_run(message: Message) -> None:
    await _show_screen(message, texts.RUN_STUB)


@router.message(F.text == BTN_STOP)
@router.message(Command("stop"))
async def on_stop(message: Message) -> None:
    await _show_screen(message, texts.STOP_STUB)


@router.message(F.text == BTN_DRY)
@router.message(Command("dry"))
async def on_dry(message: Message) -> None:
    await _show_screen(message, texts.DRY_RUN_STUB)


@router.message(Command("status"))
async def on_status(message: Message) -> None:
    await _show_screen(message, texts.STATUS_STUB)


@router.message(F.text == BTN_SCHEDULE)
async def on_schedule(message: Message) -> None:
    await _show_screen(message, texts.SCHEDULE_OVERVIEW)


@router.message(F.text == BTN_ACCOUNTS)
async def on_accounts(message: Message) -> None:
    await _show_screen(message, texts.ACCOUNTS_EMPTY)


@router.message(F.text == BTN_RESUMES)
async def on_resumes(message: Message) -> None:
    await _show_screen(message, texts.RESUMES_EMPTY)


@router.message(F.text == BTN_SETTINGS)
async def on_settings(message: Message) -> None:
    await _show_screen(message, texts.SETTINGS_OVERVIEW)


@router.message(F.text == BTN_STATS)
async def on_stats(message: Message) -> None:
    await _show_screen(message, texts.STATS_EMPTY)


@router.message(F.text == BTN_MINIAPP)
async def on_miniapp(message: Message) -> None:
    await _show_screen(message, texts.MINIAPP_STUB)


@router.message(F.text == BTN_HELP)
async def on_help_button(message: Message) -> None:
    await message.answer(
        texts.HELP_TEXT, parse_mode="Markdown", reply_markup=main_menu_kb()
    )


@router.message(F.text.startswith(BTN_ATTENTION))
async def on_attention(message: Message) -> None:
    await _show_screen(message, texts.ATTENTION_EMPTY)
