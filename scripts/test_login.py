"""Standalone test for hh.ru login (without Telegram)."""

import asyncio
import sys

from core.hh.auth import LoginError, start_login


async def main(login: str) -> None:
    try:
        s = await start_login(user_id=999, login=login)
        print(f"OK: OTP form ready, url={s.page.url}")
        await s.close()
    except LoginError as e:
        print(f"LoginError: {e}")
    except Exception as e:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        print(f"OtherError: {type(e).__name__}: {e}")


if __name__ == "__main__":
    login = sys.argv[1] if len(sys.argv) > 1 else "+79931572985"
    asyncio.run(main(login))
