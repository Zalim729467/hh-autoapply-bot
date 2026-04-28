"""Symmetric encryption helpers (Fernet) for storing hh.ru session cookies.

Key source: settings.COOKIES_ENC_KEY (URL-safe base64, 32 raw bytes).
Generate a fresh key with:  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from core.config import settings


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    if not settings.COOKIES_ENC_KEY:
        raise RuntimeError("COOKIES_ENC_KEY is not set in environment")
    return Fernet(settings.COOKIES_ENC_KEY.encode())


def encrypt_bytes(data: bytes) -> bytes:
    return _fernet().encrypt(data)


def decrypt_bytes(token: bytes) -> bytes:
    try:
        return _fernet().decrypt(token)
    except InvalidToken as e:
        raise ValueError("Cannot decrypt cookies: invalid token or wrong key") from e


def encrypt_cookies(cookies: list[dict[str, Any]]) -> bytes:
    """Serialize a Playwright cookie list to JSON, then encrypt."""
    raw = json.dumps(cookies, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return encrypt_bytes(raw)


def decrypt_cookies(token: bytes) -> list[dict[str, Any]]:
    raw = decrypt_bytes(token)
    return json.loads(raw.decode("utf-8"))
