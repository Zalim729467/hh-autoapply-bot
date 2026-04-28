"""hh.ru SMS/email-code login via Playwright.

Flow:
1. Open https://hh.ru/account/login
2. Fill the login field with email or phone, click "Continue".
3. hh.ru sends a numeric code (SMS for phone, email for address).
4. Wait for the code-input form to appear; report back to caller.
5. Caller calls submit_code(); we type the code, click submit, wait for redirect.
6. On success — extract cookies and close the browser.

The browser/page lives in memory between steps; caller is responsible for
keeping a reference (see core.hh.sessions). Each LoginSession has a hard
timeout of 3 minutes — after that, browser is closed and session is dropped.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeout,
    async_playwright,
)

from core.config import get_settings
from core.logging import get_logger

log = get_logger("hh.auth")

LOGIN_URL = "https://hh.ru/account/login?backurl=%2F"
SESSION_TTL = timedelta(minutes=3)
NAV_TIMEOUT_MS = 60_000
# Resources we don't need for the login flow — block them to speed things up
# and save proxy traffic. hh.ru's login page works fine without them.
_BLOCKED_RESOURCE_TYPES = {"image", "media", "font", "stylesheet"}

# Selectors — kept in one place for easy patching when hh.ru tweaks the DOM.
# hh.ru login flow (April 2026):
#   Step 1 (account-type page): radio APPLICANT/EMPLOYER pre-selected to APPLICANT,
#                               click "Войти" (data-qa="submit-button").
#   Step 2 (credentials page): radio PHONE/EMAIL (PHONE pre-selected),
#                              fill phone number into [data-qa="magritte-phone-input-national-number-input"]
#                              (national digits only, no +7),
#                              OR switch to EMAIL radio + fill email field.
#                              Click "Дальше" (data-qa="submit-button") → triggers SMS/email.
#   Step 3: OTP form appears, fill code, submit, redirect to / or /applicant.
SEL_STEP1_SUBMIT = 'button[data-qa="submit-button"]'
SEL_PHONE_RADIO = 'input[data-qa="credential-type-PHONE"]'
SEL_EMAIL_RADIO = 'input[data-qa="credential-type-EMAIL"]'
SEL_PHONE_INPUT = 'input[data-qa="magritte-phone-input-national-number-input"]'
SEL_EMAIL_INPUT = (
    'input[data-qa="login-input-username"], input[data-qa="login-input-email"], '
    'input[name="username"], input[name="login"], input[type="email"]'
)
SEL_STEP2_SUBMIT = 'button[data-qa="submit-button"]'
SEL_CODE_INPUT = (
    'input[data-qa="magritte-pincode-input-field"], '
    'input[data-qa="otp-code-input"], input[name="otp"], input[name="otpCode"], '
    'input[autocomplete="one-time-code"], input[data-qa="account-signup-confirmation-code"]'
)
SEL_CODE_SUBMIT = 'button[data-qa="submit-button"], button[type="submit"]'
# After successful login hh.ru redirects either to "/" or "/applicant".
SUCCESS_URL_RE = re.compile(
    r"^https?://(?:[\w-]+\.)?hh\.ru(/$|/applicant|/profile|/(?!account/))"
)


@dataclass
class LoginSession:
    user_id: int
    login: str
    pw: Playwright
    browser: Browser
    context: BrowserContext
    page: Page
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    code_attempts: int = 0

    @property
    def expired(self) -> bool:
        return datetime.now(timezone.utc) - self.created_at > SESSION_TTL

    async def close(self) -> None:
        try:
            await self.context.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            await self.browser.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            await self.pw.stop()
        except Exception:  # noqa: BLE001
            pass


class LoginError(Exception):
    """Raised when hh.ru rejects the login or code."""


async def start_login(user_id: int, login: str) -> LoginSession:
    """Step 1: open login page, submit username, wait for code input.

    Returns a LoginSession that the caller must hand to submit_code() later.
    On any failure, the browser is cleaned up before raising.
    """
    pw = await async_playwright().start()
    proxy_url = (get_settings().HH_PROXY_URL or "").strip()
    launch_kwargs: dict[str, Any] = {
        "headless": True,
        "args": [
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            # Mobile/shared proxies often choke on multiplexed HTTP/2 + QUIC
            # tunnels — force plain HTTP/1.1 over a single CONNECT each.
            "--disable-http2",
            "--disable-quic",
            "--disable-features=NetworkService,UseDnsHttpsSvcb",
        ],
    }
    if proxy_url:
        launch_kwargs["proxy"] = _build_proxy(proxy_url)
        log.info(
            "hh_login_proxy", user_id=user_id, server=launch_kwargs["proxy"]["server"]
        )
    browser = await pw.chromium.launch(**launch_kwargs)
    context = await browser.new_context(
        locale="ru-RU",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/130.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
    )
    page = await context.new_page()
    page.set_default_timeout(NAV_TIMEOUT_MS)

    async def _block(route):  # type: ignore[no-untyped-def]
        if route.request.resource_type in _BLOCKED_RESOURCE_TYPES:
            await route.abort()
        else:
            await route.continue_()

    await page.route("**/*", _block)

    session = LoginSession(
        user_id=user_id,
        login=login,
        pw=pw,
        browser=browser,
        context=context,
        page=page,
    )

    try:
        log.info("hh_login_open", user_id=user_id)
        response = await _goto_with_retry(page, LOGIN_URL, user_id=user_id, attempts=4)
        status = response.status if response else 0
        # hh.ru blocks suspicious IPs (datacenter / known VPN exits) with a stub
        # page or HTTP 451. Detect this early so the user gets a clear message.
        body_preview = await _safe_body_text(page)
        body_low = body_preview.lower()
        if (
            status in (403, 451)
            or "vpn мешает" in body_low
            or "vpn мешает работе" in body_low
        ):
            log.warning(
                "hh_login_blocked_ip",
                user_id=user_id,
                status=status,
                body_preview=body_preview[:200],
            )
            raise LoginError(
                "hh.ru заблокировал IP-адрес сервера (видит его как VPN/прокси, HTTP "
                f"{status or '???'}). Нужен российский IP: переключи VPN на RU-сервер "
                "или отключи его, либо настрой residential-прокси для аккаунта."
            )
        # Step 1: account-type page (APPLICANT pre-selected). Click "Войти".
        try:
            await page.wait_for_selector(
                SEL_STEP1_SUBMIT, state="visible", timeout=NAV_TIMEOUT_MS
            )
        except PlaywrightTimeout as e:
            body = await _safe_body_text(page)
            log.warning(
                "hh_login_no_step1",
                user_id=user_id,
                url=page.url,
                body_preview=body[:300],
            )
            raise LoginError(
                f"На странице нет кнопки «Войти». URL: {page.url}. "
                f"Начало текста: «{body[:120].strip()}…». "
                "Скорее всего hh.ru показал заглушку (антибот/VPN-блок)."
            ) from e
        await page.click(SEL_STEP1_SUBMIT)
        log.info("hh_login_step1_clicked", user_id=user_id)

        # Step 2: PHONE/EMAIL form. Fill credential and submit.
        is_email = "@" in login
        try:
            if is_email:
                # Switch to EMAIL tab if needed.
                try:
                    await page.click(SEL_EMAIL_RADIO, timeout=5000)
                except PlaywrightTimeout:
                    pass
                email_input = page.locator(SEL_EMAIL_INPUT).first
                await email_input.wait_for(state="visible", timeout=NAV_TIMEOUT_MS)
                await email_input.click()
                await email_input.press_sequentially(login, delay=30)
            else:
                # PHONE: hh.ru wants national digits only (no +7 / no country code).
                national = re.sub(r"\D", "", login)
                if national.startswith("7") and len(national) == 11:
                    national = national[1:]
                elif national.startswith("8") and len(national) == 11:
                    national = national[1:]
                phone_input = page.locator(SEL_PHONE_INPUT)
                await phone_input.wait_for(state="visible", timeout=NAV_TIMEOUT_MS)
                # IMPORTANT: hh.ru's form is React-based — page.fill() bypasses
                # the synthetic events React listens for, leaving the submit
                # button disabled. Type the digits one-by-one to fire real
                # input events.
                await phone_input.click()
                await phone_input.press_sequentially(national, delay=40)
        except PlaywrightTimeout as e:
            body = await _safe_body_text(page)
            log.warning(
                "hh_login_no_credential_form",
                user_id=user_id,
                url=page.url,
                body_preview=body[:300],
            )
            raise LoginError(
                f"Не появилась форма ввода {'email' if is_email else 'телефона'}. "
                f"URL: {page.url}."
            ) from e

        # Wait for submit button to become enabled (form validated).
        submit_btn = page.locator(SEL_STEP2_SUBMIT)
        try:
            await submit_btn.wait_for(state="visible", timeout=NAV_TIMEOUT_MS)
            # The button has `disabled` attribute while form is invalid /
            # while async validation is loading.
            await page.wait_for_function(
                """sel => {
                    const b = document.querySelector(sel);
                    return b && !b.disabled && !b.className.includes('loading');
                }""",
                arg=SEL_STEP2_SUBMIT,
                timeout=15_000,
            )
        except PlaywrightTimeout as e:
            body = await _safe_body_text(page)
            log.warning(
                "hh_login_submit_disabled",
                user_id=user_id,
                url=page.url,
                body_preview=body[:300],
            )
            raise LoginError(
                "Кнопка «Дальше» не активировалась. Проверь правильность номера/email."
            ) from e

        await submit_btn.click()
        log.info(
            "hh_login_step2_clicked",
            user_id=user_id,
            kind="email" if is_email else "phone",
        )

        # Detect captcha: hh.ru shows a "Пройдите капчу" modal after suspicious
        # activity (many login attempts from same IP / phone). Without solving
        # it, no SMS will be sent.
        try:
            await page.wait_for_timeout(1500)
            body_now = (await _safe_body_text(page)).lower()
            if (
                "пройдите капчу" in body_now
                or "введите текст с картинки" in body_now
                or "не робот" in body_now
            ):
                log.warning("hh_login_captcha", user_id=user_id, url=page.url)
                raise LoginError(
                    "hh.ru показал капчу (слишком много попыток входа с этого IP). "
                    "Подожди 10–15 минут и попробуй снова. "
                    "Если повторится — нужен другой прокси-IP или другой номер."
                )
        except LoginError:
            raise

        # Step 3: wait for OTP input (SMS/email code form).
        try:
            await page.wait_for_selector(
                SEL_CODE_INPUT, state="visible", timeout=NAV_TIMEOUT_MS
            )
        except PlaywrightTimeout as e:
            # Capture page text to help diagnose.
            body = await _safe_body_text(page)
            log.warning(
                "hh_login_no_otp",
                user_id=user_id,
                url=page.url,
                body_preview=body[:300],
            )
            raise LoginError(
                "Не дождался формы ввода кода. Возможно, неверный логин или hh.ru запросил пароль/капчу."
            ) from e
        log.info("hh_login_otp_ready", user_id=user_id)
        return session
    except LoginError:
        await session.close()
        raise
    except Exception as e:  # noqa: BLE001
        log.exception("hh_login_start_failed", user_id=user_id)
        await session.close()
        raise LoginError(f"Не удалось открыть страницу авторизации: {e}") from e


async def submit_code(session: LoginSession, code: str) -> list[dict[str, Any]]:
    """Step 2: type the SMS/email code, submit, wait for success redirect.

    Returns the cookie list on success. On bad code, raises LoginError but
    KEEPS the session alive so the user can retry (up to 3 attempts).
    On any other failure, closes the session and raises.
    """
    if session.expired:
        await session.close()
        raise LoginError("Сессия истекла (3 мин). Начни заново.")

    session.code_attempts += 1
    page = session.page
    try:
        # OTP form on hh.ru is a "pincode" field (one input that accepts the
        # whole code) — there's NO submit button at all. The form auto-submits
        # via JS as soon as the last digit is typed, so we just type the code
        # character-by-character and wait for the navigation.
        code_input = page.locator(SEL_CODE_INPUT).first
        await code_input.click()
        await code_input.fill("")  # clear previous attempt
        await code_input.press_sequentially(code, delay=80)

        # If a submit button does exist (older flow), click it; otherwise rely
        # on the auto-submit.
        try:
            submit_btn = page.locator(SEL_CODE_SUBMIT).first
            if await submit_btn.count():
                try:
                    await page.wait_for_function(
                        """sel => {
                            const btns = document.querySelectorAll(sel);
                            for (const b of btns) {
                                if (!b.disabled && !b.className.includes('loading')) return true;
                            }
                            return false;
                        }""",
                        arg=SEL_CODE_SUBMIT,
                        timeout=5_000,
                    )
                    await submit_btn.click()
                except PlaywrightTimeout:
                    pass  # auto-submit will handle it
        except Exception:
            pass

        # Race: success URL OR error message appears.
        try:
            await page.wait_for_url(SUCCESS_URL_RE, timeout=NAV_TIMEOUT_MS)
        except PlaywrightTimeout:
            # Maybe the code was wrong — give the user another try.
            still_on_login = "account/login" in page.url
            body = await _safe_body_text(page)
            looks_like_bad_code = any(
                marker in body.lower()
                for marker in ("неверный код", "неправильный код", "истёк", "истек")
            )
            if still_on_login or looks_like_bad_code:
                log.info(
                    "hh_login_bad_code",
                    user_id=session.user_id,
                    attempt=session.code_attempts,
                )
                if session.code_attempts >= 3:
                    await session.close()
                    raise LoginError("Слишком много попыток. Начни заново.")
                raise LoginError("Неверный код. Попробуй ещё раз.")
            await session.close()
            log.warning(
                "hh_login_unknown_state",
                user_id=session.user_id,
                url=page.url,
                body=body[:300],
            )
            raise LoginError("hh.ru не подтвердил вход. Попробуй позже.")

        cookies = await session.context.cookies()
        log.info(
            "hh_login_success",
            user_id=session.user_id,
            cookie_count=len(cookies),
            final_url=page.url,
        )
        # Close browser in background — sometimes Playwright/proxy hangs on
        # close and we don't want to block returning cookies to the caller.
        try:
            await asyncio.wait_for(session.close(), timeout=10)
        except (asyncio.TimeoutError, Exception) as e:  # noqa: BLE001
            log.warning("hh_login_close_slow", user_id=session.user_id, error=str(e))
        return cookies
    except LoginError:
        raise
    except Exception as e:  # noqa: BLE001
        log.exception("hh_login_submit_failed", user_id=session.user_id)
        await session.close()
        raise LoginError(f"Ошибка при отправке кода: {e}") from e


async def _safe_body_text(page: Page) -> str:
    try:
        return await asyncio.wait_for(page.inner_text("body"), timeout=2)
    except Exception:  # noqa: BLE001
        return ""


# Connection errors that mobile/shared proxies frequently throw on the first
# few CONNECT tunnels. They are usually transient — a 1–2 second wait and a
# retry succeeds. Match by substring inside the Playwright error message.
_RETRYABLE_NET_ERRORS = (
    "ERR_TUNNEL_CONNECTION_FAILED",
    "ERR_CONNECTION_CLOSED",
    "ERR_CONNECTION_RESET",
    "ERR_PROXY_CONNECTION_FAILED",
    "ERR_EMPTY_RESPONSE",
    "ERR_TIMED_OUT",
    "ERR_ABORTED",
    "ERR_HTTP2_PROTOCOL_ERROR",
    "ERR_QUIC_PROTOCOL_ERROR",
    "ERR_SOCKS_CONNECTION_FAILED",
    "ERR_NAME_NOT_RESOLVED",
    # Playwright's own navigation timeout — when the proxy hangs without
    # closing the tunnel, page.goto raises this. Treat as transient.
    "Timeout ",
    "exceeded",
)


# Use a shorter per-attempt timeout so a hung proxy fails fast and we can
# retry on a fresh tunnel rather than waiting the full nav timeout.
_GOTO_ATTEMPT_TIMEOUT_MS = 25_000


async def _goto_with_retry(page: Page, url: str, *, user_id: int, attempts: int = 5):
    """Navigate with retries on transient proxy/network errors."""
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await page.goto(
                url, wait_until="commit", timeout=_GOTO_ATTEMPT_TIMEOUT_MS
            )
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            retryable = any(code in msg for code in _RETRYABLE_NET_ERRORS)
            log.warning(
                "hh_login_goto_failed",
                user_id=user_id,
                attempt=attempt,
                retryable=retryable,
                error=msg.splitlines()[0][:200],
            )
            last_exc = e
            if not retryable or attempt == attempts:
                raise
            await asyncio.sleep(1.5 * attempt)
    assert last_exc is not None
    raise last_exc


def _build_proxy(url: str) -> dict[str, str]:
    """Parse proxy URL into Playwright's launch(proxy=...) dict.

    Accepts: http://user:pass@host:port, https://..., socks5://..., or just
    host:port (treated as http://). Username/password are split out because
    Playwright's Chromium requires them as separate fields.
    """
    from urllib.parse import urlparse

    raw = url.strip()
    if "://" not in raw:
        raw = "http://" + raw
    parsed = urlparse(raw)
    if not parsed.hostname or not parsed.port:
        raise LoginError(f"Некорректный HH_PROXY_URL: {url!r}")
    server = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
    out: dict[str, str] = {"server": server}
    if parsed.username:
        out["username"] = parsed.username
    if parsed.password:
        out["password"] = parsed.password
    return out
