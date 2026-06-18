"""鉴权原语：密码哈希、API Key 生成与校验。

JWT 签发/校验与 FastAPI 依赖（当前 org/user 解析）在 M1 末/M4 完善。
"""

from __future__ import annotations

import hashlib
import secrets

from passlib.context import CryptContext

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

API_KEY_PREFIX = "oa_"


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _pwd.verify(password, hashed)


def generate_api_key() -> tuple[str, str, str]:
    """返回 (明文 key, 前缀, 哈希)。明文仅创建时返回一次，库中仅存哈希。"""
    token = secrets.token_urlsafe(32)
    plaintext = f"{API_KEY_PREFIX}{token}"
    prefix = plaintext[: len(API_KEY_PREFIX) + 6]
    return plaintext, prefix, hash_api_key(plaintext)


def hash_api_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()
