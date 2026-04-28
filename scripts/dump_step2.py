"""Click 'Войти' on hh.ru login page and dump next step."""

import asyncio
from playwright.async_api import async_playwright
from core.config import get_settings
from core.hh.auth import _build_proxy


async def main() -> None:
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
    for _ in range(3):
        try:
            await page.goto(
                "https://hh.ru/account/login?backurl=%2F",
                wait_until="domcontentloaded",
                timeout=60_000,
            )
            break
        except Exception as e:
            print("retry goto:", e)
            await asyncio.sleep(2)
    print("STEP1 url:", page.url)
    await page.wait_for_timeout(1500)
    # Click "Войти"
    await page.click('button[data-qa="submit-button"]')
    print("clicked submit-button")
    await page.wait_for_timeout(3000)
    print("STEP2 url:", page.url)
    inputs = await page.evaluate(
        """() => Array.from(document.querySelectorAll('input')).map(i => ({name:i.name, type:i.type, dq:i.getAttribute('data-qa'), placeholder:i.placeholder, ac:i.autocomplete}))"""
    )
    buttons = await page.evaluate(
        """() => Array.from(document.querySelectorAll('button')).slice(0, 20).map(b => ({text:(b.innerText||'').trim().slice(0,60), dq:b.getAttribute('data-qa'), type:b.type}))"""
    )
    print("INPUTS:")
    for i in inputs:
        print(" ", i)
    print("BUTTONS:")
    for b in buttons:
        if b["text"] or b["dq"]:
            print(" ", b)
    await browser.close()
    await pw.stop()


if __name__ == "__main__":
    asyncio.run(main())
