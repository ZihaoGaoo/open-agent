"""应用配置。所有运行期参数通过环境变量注入（见 .env.example）。"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 基础
    app_name: str = "open-agent"
    role: Literal["web", "worker"] = "web"
    environment: Literal["dev", "prod"] = "dev"
    log_level: str = "INFO"

    # 数据库（asyncpg）
    database_url: str = "postgresql+asyncpg://openagent:openagent@localhost:5432/openagent"

    # 默认 LLM Provider
    anthropic_api_key: str | None = None
    default_model: str = "claude-opus-4-8"

    # 安全
    secret_encryption_key: str | None = None  # Fernet key，用于凭据加密
    jwt_secret: str = "dev-insecure-change-me"

    # 可选
    redis_url: str | None = None

    @property
    def alembic_url(self) -> str:
        """Alembic 用的 URL（与 async URL 同源，env.py 内按需转换）。"""
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
