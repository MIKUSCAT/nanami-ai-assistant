"""ToDo管理工具 - 提供任务清单的增删改查功能"""
from __future__ import annotations

from typing import Any, Dict, Optional, List
from .base import BaseTool
from services.todo_store import (
    list_todos,
    create_todo,
    update_todo,
    delete_todo,
    reorder_todos,
)
from schemas.todo import TodoCreate, TodoUpdate, TodoStatus, TodoPriority, TodoAgentType


class TodoListTool(BaseTool):
    """列出所有待办任务"""

    name = "list_todos"
    description = "列出所有待办任务。返回任务列表，包含每个任务的id、标题、描述、状态和创建时间。"

    async def execute(self, session_id: str = "default") -> Dict[str, Any]:
        try:
            todos = list_todos(session_id=session_id)  # ✅ 传递session_id
            return {
                "error": False,
                "data": {
                    "todos": [t.model_dump() for t in todos],
                    "count": len(todos)
                }
            }
        except Exception as e:
            return {"error": True, "message": f"列出任务失败: {str(e)}"}


class TodoCreateTool(BaseTool):
    """创建新的待办任务"""

    name = "create_todo"
    description = "创建新的待办任务。需要提供任务标题，可选提供描述和状态。"

    async def execute(
        self,
        title: str,
        description: Optional[str] = None,
        status: str = "pending",
        priority: str = "medium",
        agent_type: str = "main",
        session_id: str = "default"  # ✅ 新增：session_id参数
    ) -> Dict[str, Any]:
        try:
            # 验证状态
            if status not in ["pending", "in_progress", "completed"]:
                return {
                    "error": True,
                    "message": f"无效的状态: {status}，必须是 pending/in_progress/completed"
                }

            # 验证优先级
            if priority not in ["high", "medium", "low"]:
                return {
                    "error": True,
                    "message": f"无效的优先级: {priority}，必须是 high/medium/low"
                }

            # 验证Agent类型
            if agent_type not in ["main", "search", "browser", "windows", "custom"]:
                return {
                    "error": True,
                    "message": f"无效的Agent类型: {agent_type}"
                }

            todo_data = TodoCreate(
                title=title,
                description=description,
                status=TodoStatus(status),
                priority=TodoPriority(priority),
                agent_type=TodoAgentType(agent_type)
            )
            todo = create_todo(todo_data, session_id=session_id)  # ✅ 传递session_id

            return {
                "error": False,
                "data": {
                    "todo": todo.model_dump(),
                    "message": f"任务创建成功: {title}"
                }
            }
        except Exception as e:
            return {"error": True, "message": f"创建任务失败: {str(e)}"}


class TodoUpdateTool(BaseTool):
    """更新待办任务"""

    name = "update_todo"
    description = "更新待办任务的信息。需要提供任务ID，可以更新标题、描述或状态。"

    async def execute(
        self,
        todo_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        session_id: str = "default"  # ✅ 新增：session_id参数
    ) -> Dict[str, Any]:
        try:
            # 验证状态
            if status and status not in ["pending", "in_progress", "completed"]:
                return {
                    "error": True,
                    "message": f"无效的状态: {status}"
                }

            # 验证优先级
            if priority and priority not in ["high", "medium", "low"]:
                return {
                    "error": True,
                    "message": f"无效的优先级: {priority}"
                }

            update_data = TodoUpdate(
                title=title,
                description=description,
                status=TodoStatus(status) if status else None,
                priority=TodoPriority(priority) if priority else None
            )

            todo = update_todo(todo_id, update_data, session_id=session_id)  # ✅ 传递session_id
            if not todo:
                return {
                    "error": True,
                    "message": f"任务不存在: {todo_id}"
                }

            return {
                "error": False,
                "data": {
                    "todo": todo.model_dump(),
                    "message": "任务更新成功"
                }
            }
        except Exception as e:
            return {"error": True, "message": f"更新任务失败: {str(e)}"}


class TodoDeleteTool(BaseTool):
    """删除待办任务"""

    name = "delete_todo"
    description = "删除指定的待办任务。需要提供任务ID。"

    async def execute(self, todo_id: str, session_id: str = "default") -> Dict[str, Any]:
        try:
            success = delete_todo(todo_id, session_id=session_id)  # ✅ 传递session_id
            if not success:
                return {
                    "error": True,
                    "message": f"任务不存在: {todo_id}"
                }

            return {
                "error": False,
                "data": {
                    "deleted": True,
                    "message": "任务删除成功"
                }
            }
        except Exception as e:
            return {"error": True, "message": f"删除任务失败: {str(e)}"}


class TodoReorderTool(BaseTool):
    """重排待办任务顺序"""

    name = "reorder_todos"
    description = "根据提供的任务ID顺序，重排ToDo列表的顺序。需要提供任务ID数组，数组顺序即新的顺序。"

    async def execute(self, order: List[str], session_id: str = "default") -> Dict[str, Any]:
        try:
            if not isinstance(order, list) or not all(isinstance(x, str) for x in order):
                return {"error": True, "message": "参数 order 必须是字符串ID数组"}
            todos = reorder_todos(order, session_id=session_id)  # ✅ 传递session_id
            return {
                "error": False,
                "data": {
                    "todos": [t.model_dump() for t in todos],
                    "message": "重排成功"
                }
            }
        except Exception as e:
            return {"error": True, "message": f"重排失败: {str(e)}"}
