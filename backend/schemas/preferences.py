"""用户偏好提取的数据模型。"""
from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ExtractPreferencesRequest(BaseModel):
    """提取用户偏好的请求模型"""
    messages: List[Dict[str, Any]] = Field(
        ...,
        description="对话历史消息数组，格式：[{'role': 'user|assistant', 'content': '...'}]"
    )
