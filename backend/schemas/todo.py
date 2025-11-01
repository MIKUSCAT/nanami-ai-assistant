"""待办清单（ToDo）数据模型。"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TodoStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"


class TodoPriority(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class TodoAgentType(str, Enum):
    main = "main"  # 主Agent的TODO
    search = "search"  # SearchSubAgent的TODO
    browser = "browser"  # BrowserSubAgent的TODO
    windows = "windows"  # WindowsSubAgent的TODO
    custom = "custom"  # 自定义SubAgent的TODO


class TodoCreate(BaseModel):
    title: str = Field(..., description="任务标题")
    description: Optional[str] = Field(None, description="任务描述")
    status: TodoStatus = Field(TodoStatus.pending, description="任务状态")
    priority: TodoPriority = Field(TodoPriority.medium, description="任务优先级")
    agent_type: TodoAgentType = Field(TodoAgentType.main, description="创建Agent类型")


class TodoUpdate(BaseModel):
    title: Optional[str] = Field(None, description="任务标题")
    description: Optional[str] = Field(None, description="任务描述")
    status: Optional[TodoStatus] = Field(None, description="任务状态")
    priority: Optional[TodoPriority] = Field(None, description="任务优先级")


class Todo(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: TodoStatus = TodoStatus.pending
    priority: TodoPriority = TodoPriority.medium
    agent_type: TodoAgentType = TodoAgentType.main
    order: int = 0
    created_at: float
    updated_at: float
    previous_status: Optional[TodoStatus] = None  # 跟踪状态变化

