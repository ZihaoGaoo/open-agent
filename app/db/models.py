"""ORM 模型。

本里程碑(M1)落地核心表：orgs / users / api_keys / agents / agent_versions / prompts。
其余表（mcp_servers、skills、webhook_tools、credentials、sessions、messages、runs、
run_events、memories、im_channels、im_identities、agent_messages、usage_records、
audit_logs）按各自里程碑在此文件追加。
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Org(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """租户。所有资源都归属某个 org。"""

    __tablename__ = "orgs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="org")
    agents: Mapped[list["Agent"]] = relationship(back_populates="org")


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """控制台用户。"""

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("org_id", "email", name="uq_users_org_email"),)

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="member", nullable=False)

    org: Mapped[Org] = relationship(back_populates="users")


class ApiKey(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """程序调用用的 API Key（仅存哈希；明文仅创建时返回一次）。"""

    __tablename__ = "api_keys"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    prefix: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    hashed_key: Mapped[str] = mapped_column(String(255), nullable=False)
    revoked: Mapped[bool] = mapped_column(default=False, nullable=False)


class Prompt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """系统提示词模板 + 变量定义。"""

    __tablename__ = "prompts"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template: Mapped[str] = mapped_column(Text, nullable=False)
    # 变量 schema（名称、类型、默认值等）
    variables: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class Agent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Agent 定义。可变配置存于 agent_versions；本表保存当前指针与元信息。"""

    __tablename__ = "agents"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_version: Mapped[int] = mapped_column(default=1, nullable=False)

    org: Mapped[Org] = relationship(back_populates="agents")
    versions: Mapped[list["AgentVersion"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )


class AgentVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Agent 配置的不可变版本快照（模型、提示词、参数、能力绑定）。"""

    __tablename__ = "agent_versions"
    __table_args__ = (
        UniqueConstraint("agent_id", "version", name="uq_agent_versions_agent_version"),
    )

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(nullable=False)

    model: Mapped[str] = mapped_column(String(128), nullable=False)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 运行参数：effort / max_tokens / thinking 等
    params: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # 能力绑定快照（mcp/skill/webhook/prompt 的引用 id 列表）。
    # 规范化的多对多关系表（agent_capability_bindings）在 M2 引入。
    capabilities: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    agent: Mapped[Agent] = relationship(back_populates="versions")
