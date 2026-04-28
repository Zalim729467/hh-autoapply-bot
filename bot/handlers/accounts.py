"""Accounts screen + Add-account FSM (§5.4 / §5.5).

Stage 3 scope:
- Show list of linked hh.ru accounts (or empty state).
- "Add account" — Playwright-based SMS/email login, encrypted cookie storage.
- No resume loading yet — that's stage 4.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from bot import texts
from bot.keyboards.accounts import (
    BTN_ADD_ACCOUNT,
    BTN_CANCEL,
    accounts_empty_kb,
    accounts_full_kb,
    cancel_only_kb,
)
from bot.keyboards.main_menu import BTN_ACCOUNTS, BTN_BACK, main_menu_kb
from bot.states import AddAccount
from core.db.models import HhAccount, User
from core.db.session import SessionLocal
from core.hh.auth import LoginError, start_login, submit_code
from core.hh.sessions import session_store
from core.logging import get_logger
from core.security.crypto import encrypt_cookies

router = Router(name="accounts")
log = get_logger("accounts")

MAX_ACCOUNTS_PER_USER = 2

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?\d[\d\s\-()]{8,18}\d$")


# --- Helpers ---


def _normalize_login(raw: str) -> str | None:
    """Return normalized login (email lower-cased, phone digits-only with +) or None."""
    s = raw.strip()
    if EMAIL_RE.match(s):
        return s.lower()
    if PHONE_RE.match(s):
        digits = re.sub(r"\D", "", s)
        if digits.startswith("8") and len(digits) == 11:
            digits = "7" + digits[1:]
        if len(digits) == 10:
            digits = "7" + digits
        return "+" + digits
    return None


def _mask_login(login: str) -> str:
    if "@" in login:
        local, _, domain = login.partition("@")
        head = local[:3] if len(local) > 3 else local[:1]
        return f"{head}•••@{domain}"
    # phone
    if len(login) >= 6:
        return f"{login[:2]} ••• •• {login[-2:]}"
    return "•••"


async def _list_accounts(user_id: int) -> list[HhAccount]:
    async with SessionLocal() as session:
        rows = (
            (
                await session.execute(
                    select(HhAccount)
                    .where(HhAccount.user_id == user_id)
                    .order_by(HhAccount.id)
                )
            )
            .scalars()
            .all()
        )
        return list(rows)


def _format_account_card(acc: HhAccount) -> str:
    status_icon = "🟢" if acc.status == "active" else "🔴"
    last = (
        acc.last_auth_at.strftime("%d.%m %H:%M")
        if acc.last_auth_at is not None
        else "—"
    )
    return (
        f"📧 *{_mask_login(acc.login)}*   {status_icon} {acc.status}\n"
        f"   последняя авторизация: {last}"
    )


async def _show_accounts_screen(message: Message, user: User) -> None:
    accounts = await _list_accounts(user.id)
    if not accounts:
        await message.answer(
            texts.ACCOUNTS_EMPTY,
            parse_mode="Markdown",
            reply_markup=accounts_empty_kb(),
        )
        return

    body = texts.ACCOUNTS_LIST_HEADER + "\n\n".join(
        _format_account_card(a) for a in accounts
    )
    if len(accounts) >= MAX_ACCOUNTS_PER_USER:
        try:
            await message.answer(
                body + texts.ACCOUNTS_LIMIT_REACHED,
                parse_mode="Markdown",
                reply_markup=accounts_full_kb(),
            )
        except Exception:
            log.exception("accounts_render_failed", user_id=user.id)
            await message.answer(
                body + texts.ACCOUNTS_LIMIT_REACHED,
                reply_markup=accounts_full_kb(),
            )
    else:
        try:
            await message.answer(
                body, parse_mode="Markdown", reply_markup=accounts_empty_kb()
            )
        except Exception:
            log.exception("accounts_render_failed", user_id=user.id)
            await message.answer(body, reply_markup=accounts_empty_kb())


# --- Entry: button or /accounts ---


@router.message(F.text == BTN_ACCOUNTS)
@router.message(Command("accounts"))
async def on_accounts(message: Message, user: User, state: FSMContext) -> None:
    # Make sure no stale FSM is in the way.
    await state.clear()
    await session_store.discard(user.id)
    await _show_accounts_screen(message, user)


# --- Add account — start FSM ---


@router.message(F.text == BTN_ADD_ACCOUNT)
async def on_add_account(message: Message, user: User, state: FSMContext) -> None:
    accounts = await _list_accounts(user.id)
    if len(accounts) >= MAX_ACCOUNTS_PER_USER:
        await message.answer(
            texts.ACCOUNTS_LIMIT_REACHED.lstrip(), parse_mode="Markdown"
        )
        return
    await state.set_state(AddAccount.waiting_login)
    await message.answer(
        texts.ADD_ACCOUNT_INTRO,
        parse_mode="Markdown",
        reply_markup=cancel_only_kb(),
    )


# --- Cancel anywhere in the FSM ---


@router.message(AddAccount.waiting_login, F.text == BTN_CANCEL)
@router.message(AddAccount.waiting_code, F.text == BTN_CANCEL)
async def on_cancel_add(message: Message, user: User, state: FSMContext) -> None:
    await state.clear()
    await session_store.discard(user.id)
    await message.answer(texts.ADD_ACCOUNT_CANCELED, reply_markup=main_menu_kb())


# --- Step 1: receive login, kick off Playwright ---


@router.message(AddAccount.waiting_login, F.text)
async def on_login_input(message: Message, user: User, state: FSMContext) -> None:
    raw = message.text or ""
    login = _normalize_login(raw)
    if login is None:
        await message.answer(texts.ADD_ACCOUNT_BAD_LOGIN, parse_mode="Markdown")
        return

    await message.answer(texts.ADD_ACCOUNT_OPENING, reply_markup=cancel_only_kb())
    try:
        session = await start_login(user.id, login)
    except LoginError as e:
        await state.clear()
        await message.answer(
            texts.ADD_ACCOUNT_FAIL.format(reason=str(e)),
            parse_mode="Markdown",
            reply_markup=main_menu_kb(),
        )
        return
    except Exception as e:  # noqa: BLE001
        log.exception("add_account_unexpected", user_id=user.id)
        await state.clear()
        await message.answer(
            texts.ADD_ACCOUNT_FAIL.format(reason=f"внутренняя ошибка: {e}"),
            parse_mode="Markdown",
            reply_markup=main_menu_kb(),
        )
        return

    await session_store.put(session)
    await state.set_state(AddAccount.waiting_code)
    await state.update_data(login=login)
    await message.answer(
        texts.ADD_ACCOUNT_CODE_PROMPT.format(login=_mask_login(login)),
        parse_mode="Markdown",
        reply_markup=cancel_only_kb(),
    )


# --- Step 2: receive code, submit ---


@router.message(AddAccount.waiting_code, F.text)
async def on_code_input(message: Message, user: User, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not re.fullmatch(r"\d{4,6}", raw):
        await message.answer(texts.ADD_ACCOUNT_BAD_CODE_FORMAT)
        return

    sess = await session_store.get(user.id)
    if sess is None:
        await state.clear()
        await message.answer(
            texts.ADD_ACCOUNT_FAIL.format(reason="сессия истекла"),
            parse_mode="Markdown",
            reply_markup=main_menu_kb(),
        )
        return

    await message.answer(texts.ADD_ACCOUNT_CHECKING)

    try:
        cookies = await submit_code(sess, raw)
    except LoginError as e:
        # Bad code with retries left — keep FSM, prompt again.
        if "ещё раз" in str(e) or "ещё раз" in str(e).lower():
            await message.answer(
                texts.ADD_ACCOUNT_RETRY_CODE.format(reason=str(e)),
                reply_markup=cancel_only_kb(),
            )
            return
        # Otherwise — terminal failure.
        await session_store.discard(user.id)
        await state.clear()
        await message.answer(
            texts.ADD_ACCOUNT_FAIL.format(reason=str(e)),
            parse_mode="Markdown",
            reply_markup=main_menu_kb(),
        )
        return
    except Exception as e:  # noqa: BLE001
        log.exception("submit_code_unexpected", user_id=user.id)
        await session_store.discard(user.id)
        await state.clear()
        await message.answer(
            texts.ADD_ACCOUNT_FAIL.format(reason=f"внутренняя ошибка: {e}"),
            parse_mode="Markdown",
            reply_markup=main_menu_kb(),
        )
        return

    # Success — encrypt + persist.
    data = await state.get_data()
    login = data.get("login", sess.login)
    enc = encrypt_cookies(cookies)

    async with SessionLocal() as db:
        acc = HhAccount(
            user_id=user.id,
            login=login,
            cookies_enc=enc,
            status="active",
            last_auth_at=datetime.now(timezone.utc),
        )
        db.add(acc)
        await db.commit()

    await state.clear()
    await session_store.discard(user.id)
    await message.answer(
        texts.ADD_ACCOUNT_SUCCESS.format(login=_mask_login(login)),
        parse_mode="Markdown",
        reply_markup=main_menu_kb(),
    )
    log.info("hh_account_linked", user_id=user.id, cookie_count=len(cookies))
