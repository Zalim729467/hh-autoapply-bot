"""In-memory store of active hh.ru login sessions, keyed by Telegram user_id.

Each user can have at most one active login session at a time. Starting a new
one kicks the old one out (and closes its browser).
"""

from __future__ import annotations

import asyncio

from core.hh.auth import LoginSession
from core.logging import get_logger

log = get_logger("hh.sessions")


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[int, LoginSession] = {}
        self._lock = asyncio.Lock()

    async def put(self, session: LoginSession) -> None:
        async with self._lock:
            old = self._sessions.pop(session.user_id, None)
            if old is not None:
                await old.close()
            self._sessions[session.user_id] = session

    async def get(self, user_id: int) -> LoginSession | None:
        async with self._lock:
            sess = self._sessions.get(user_id)
            if sess is None:
                return None
            if sess.expired:
                self._sessions.pop(user_id, None)
                await sess.close()
                return None
            return sess

    async def pop(self, user_id: int) -> LoginSession | None:
        async with self._lock:
            return self._sessions.pop(user_id, None)

    async def discard(self, user_id: int) -> None:
        sess = await self.pop(user_id)
        if sess is not None:
            await sess.close()


# Process-wide singleton.
session_store = SessionStore()
