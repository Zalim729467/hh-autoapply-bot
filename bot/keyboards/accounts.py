"""Reply keyboards for the accounts screen."""

from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from bot.keyboards.main_menu import BTN_BACK

BTN_ADD_ACCOUNT = "➕ Добавить аккаунт"
BTN_CANCEL = "✖ Отмена"


def accounts_empty_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ADD_ACCOUNT)],
            [KeyboardButton(text=BTN_BACK)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def accounts_full_kb() -> ReplyKeyboardMarkup:
    """When user already has 2 accounts (limit reached)."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_BACK)]],
        resize_keyboard=True,
        is_persistent=True,
    )


def cancel_only_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_CANCEL)]],
        resize_keyboard=True,
        is_persistent=True,
    )
