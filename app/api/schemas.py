"""接入层请求/响应 DTO（Pydantic v2）。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---- Prompt ----
class PromptCreate(BaseModel):
    name: str
    template: str
    variables: dict[str, Any] = Field(default_factory=dict)


class PromptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    template: str
    variables: dict[str, Any]
    created_at: datetime


# ---- Agent ----
class AgentCreate(BaseModel):
    name: str
    description: str | None = None
    model: str | None = None  # 缺省用 settings.default_model
    system_prompt: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    capabilities: dict[str, Any] = Field(default_factory=dict)


class AgentVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version: int
    model: str
    system_prompt: str | None
    params: dict[str, Any]
    capabilities: dict[str, Any]


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    current_version: int
    created_at: datetime


# ---- Invoke ----
class InvokeRequest(BaseModel):
    input: str = Field(..., description="用户输入文本")
    variables: dict[str, Any] = Field(default_factory=dict, description="提示词变量")
    provider: str = Field(default="anthropic", description="LLM provider 名称")
    max_tokens: int | None = None


class InvokeResponse(BaseModel):
    output: str
    iterations: int
    stop_reason: str
    usage: dict[str, int]
