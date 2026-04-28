"""Aiogram FSM states (one place for all flows)."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class AddAccount(StatesGroup):
    waiting_login = State()
    waiting_code = State()
