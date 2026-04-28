"""Walk login flow and dump what the OTP page actually contains.

Usage:
  docker exec -e PYTHONPATH=/app hh-bot python scripts/dump_otp_page.py +79931572985
"""

import asyncio
import sys

from playwright.async_api import async_playwright

from core.config import get_settings
from core.hh.auth import _build_proxy


async def main(login: str) -> None:
    pw = await async_playwright().start()
    proxy = _build_proxy(get_settings().HH_PROXY_URL)
    browser = await pw.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-http2",
            "--disable-quic",
        ],
        proxy=proxy,
    )
    ctx = await browser.new_context(
        locale="ru-RU",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    )
    page = await ctx.new_page()
    for _ in range(5):
        try:
            await page.goto(
                "https://hh.ru/account/login?backurl=%2F",
                wait_until="commit",
                timeout=25_000,
            )
            break
        except Exception as e:
            print("retry goto:", e)
            await asyncio.sleep(2)
    await page.wait_for_selector('button[data-qa="submit-button"]', timeout=20_000)
    await page.click('button[data-qa="submit-button"]')
    await page.wait_for_selector(
        'input[data-qa="magritte-phone-input-national-number-input"]', timeout=20_000
    )
    national = login.lstrip("+")
    if national.startswith("7") and len(national) == 11:
        national = national[1:]
    phone = page.locator('input[data-qa="magritte-phone-input-national-number-input"]')
    await phone.click()
    await phone.press_sequentially(national, delay=40)
    await page.wait_for_function(
        """sel => { const b = document.querySelector(sel); return b && !b.disabled; }""",
        arg='button[data-qa="submit-button"]',
        timeout=15_000,
    )
    await page.click('button[data-qa="submit-button"]')
    print("clicked Дальше, waiting 5s...")
    await page.wait_for_timeout(5000)
    print("URL after submit:", page.url)
    body = await page.inner_text("body")
    print("=== BODY TEXT (first 2000 chars) ===")
    print(body[:2000])
    print("=== INPUTS ===")
    inputs = await page.evaluate(
        """() => Array.from(document.querySelectorAll('input')).map(i => ({name:i.name, type:i.type, dq:i.getAttribute('data-qa'), placeholder:i.placeholder}))"""
    )
    for i in inputs:
        print(" ", i)
    print("=== BUTTONS ===")
    buttons = await page.evaluate(
        """() => Array.from(document.querySelectorAll('button, a')).slice(0,30).map(b => ({tag:b.tagName, text:(b.innerText||'').trim().slice(0,80), dq:b.getAttribute('data-qa')}))"""
    )
    for b in buttons:
        if b["text"] or b["dq"]:
            print(" ", b)
    await browser.close()
    await pw.stop()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "+79931572985"))
