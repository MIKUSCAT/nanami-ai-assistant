"""最小 OpenAI Chat Completions 兼容请求模型。"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


RoleType = Literal["system", "user", "assistant"]


class ChatMessage(BaseModel):
    role: RoleType
    content: str


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = Field(None, description="模型名称，可覆盖指针")
    messages: List[ChatMessage]
    stream: Optional[bool] = False

