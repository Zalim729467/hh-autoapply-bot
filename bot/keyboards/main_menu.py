"""Reply keyboards used across the bot."""

from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

# --- Main menu (§5.1) ---

BTN_RUN = "▶ Запустить автоотклики"
BTN_STOP = "⏹ Остановить"
BTN_DRY = "🧪 Сухой прогон"
BTN_SCHEDULE = "⏰ Расписание"
BTN_ACCOUNTS = "👤 Аккаунты"
BTN_RESUMES = "📄 Резюме"
BTN_SETTINGS = "⚙ Настройки"
BTN_STATS = "📊 Статистика"
BTN_MINIAPP = "💎 Открыть приложение"
BTN_HELP = "❓ Помощь"
BTN_ATTENTION = "⚠ Требуют внимания"

BTN_BACK = "« Назад в меню"

ALL_MAIN_BUTTONS = {
    BTN_RUN,
    BTN_STOP,
    BTN_DRY,
    BTN_SCHEDULE,
    BTN_ACCOUNTS,
    BTN_RESUMES,
    BTN_SETTINGS,
    BTN_STATS,
    BTN_MINIAPP,
    BTN_HELP,
    BTN_ATTENTION,
}


def main_menu_kb(attention_count: int = 0) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=BTN_RUN), KeyboardButton(text=BTN_STOP)],
        [KeyboardButton(text=BTN_DRY), KeyboardButton(text=BTN_SCHEDULE)],
        [KeyboardButton(text=BTN_ACCOUNTS), KeyboardButton(text=BTN_RESUMES)],
        [KeyboardButton(text=BTN_SETTINGS), KeyboardButton(text=BTN_STATS)],
        [KeyboardButton(text=BTN_MINIAPP), KeyboardButton(text=BTN_HELP)],
    ]
    if attention_count > 0:
        rows.insert(0, [KeyboardButton(text=f"{BTN_ATTENTION} ({attention_count})")])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        is_persistent=True,
    )


def back_only_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_BACK)]],
        resize_keyboard=True,
        is_persistent=True,
    )


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
