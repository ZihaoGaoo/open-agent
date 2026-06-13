"""基于 Fernet 的对称加密。

密钥由 SECRET_ENCRYPTION_KEY 提供（生成方式见 .env.example）。
密文存入 credentials 表，仅在注入下游（MCP/Webhook/Provider）时解密。
"""

from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet

from app.config import get_settings


@lru_cache
def _fernet() -> Fernet:
    settings = get_settings()
    if not settings.secret_encryption_key:
        raise RuntimeError(
            "SECRET_ENCRYPTION_KEY 未配置；无法加解密凭据。生成方式见 .env.example。"
        )
    return Fernet(settings.secret_encryption_key.encode())


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()
