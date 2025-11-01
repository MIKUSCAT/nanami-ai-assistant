"""文件型待办清单存储（极简，无锁，按会话隔离）。

每个会话（session）拥有独立的TODO文件：data/todos/{session_id}.json
这样可以避免不同对话的TODO混在一起。
"""
from __future__ import annotations

import json
import os
import time
import uuid
from typing import Dict, List, Optional

from schemas.todo import Todo, TodoCreate, TodoUpdate, TodoStatus, TodoPriority, TodoAgentType


DATA_DIR = os.path.join(os.getcwd(), "data", "todos")


def _get_session_file(session_id: str) -> str:
    """获取session对应的TODO文件路径

    Args:
        session_id: 会话ID

    Returns:
        TODO文件的完整路径
    """
    return os.path.join(DATA_DIR, f"{session_id}.json")


def _ensure_store() -> None:
    """确保todos目录存在"""
    os.makedirs(DATA_DIR, exist_ok=True)


def _ensure_session_file(session_id: str) -> None:
    """确保session的TODO文件存在

    Args:
        session_id: 会话ID
    """
    _ensure_store()
    session_file = _get_session_file(session_id)
    if not os.path.exists(session_file):
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump({"todos": []}, f, ensure_ascii=False, indent=2)


def _smart_sort_todos(todos: List[Todo]) -> List[Todo]:
    """智能排序算法（参考Kode的YJ1算法）

    排序优先级：
    1. status: in_progress(3) > pending(2) > completed(1)
    2. priority: high(3) > medium(2) > low(1)
    3. updated_at: 新的在前
    """
    status_order = {
        TodoStatus.in_progress: 3,
        TodoStatus.pending: 2,
        TodoStatus.completed: 1
    }

    priority_order = {
        TodoPriority.high: 3,
        TodoPriority.medium: 2,
        TodoPriority.low: 1
    }

    def sort_key(todo: Todo):
        return (
            -status_order.get(todo.status, 0),  # 负号使大的在前
            -priority_order.get(todo.priority, 0),
            -todo.updated_at  # 新的在前
        )

    return sorted(todos, key=sort_key)


def _load(session_id: str) -> Dict[str, List[Dict]]:
    """加载数据，自动处理格式兼容性问题

    Args:
        session_id: 会话ID

    Returns:
        TODO数据字典
    """
    _ensure_session_file(session_id)
    session_file = _get_session_file(session_id)

    with open(session_file, "r", encoding="utf-8") as f:
        data = json.load(f)

        # 兼容处理：如果前端写入的是列表格式 []，自动转换为字典格式 {"todos": []}
        if isinstance(data, list):
            # 如果是列表，可能是旧版本或前端清理后的格式
            return {"todos": data}

        # 如果是字典但没有 todos 键，添加默认值
        if isinstance(data, dict) and "todos" not in data:
            data["todos"] = []

        return data


def _save(session_id: str, data: Dict) -> None:
    """保存TODO数据到session文件

    Args:
        session_id: 会话ID
        data: TODO数据
    """
    _ensure_store()
    session_file = _get_session_file(session_id)
    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_todos(session_id: str = "default") -> List[Todo]:
    """列出session的所有TODO

    Args:
        session_id: 会话ID，默认为"default"

    Returns:
        TODO列表（已排序）
    """
    data = _load(session_id)
    todos = [Todo(**t) for t in data.get("todos", [])]
    # 智能排序：status > priority > updated_at（参考Kode的YJ1算法）
    return _smart_sort_todos(todos)


def create_todo(payload: TodoCreate, session_id: str = "default") -> Todo:
    """创建TODO

    Args:
        payload: TODO创建参数
        session_id: 会话ID，默认为"default"

    Returns:
        创建的TODO对象
    """
    data = _load(session_id)
    now = time.time()
    new = Todo(
        id=str(uuid.uuid4()),
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        agent_type=payload.agent_type,
        order=len(data.get("todos", [])),
        created_at=now,
        updated_at=now,
    )
    data.setdefault("todos", []).append(new.model_dump())
    _save(session_id, data)
    return new


def update_todo(todo_id: str, payload: TodoUpdate, session_id: str = "default") -> Optional[Todo]:
    """更新TODO

    Args:
        todo_id: TODO ID
        payload: 更新参数
        session_id: 会话ID，默认为"default"

    Returns:
        更新后的TODO对象，如果不存在则返回None
    """
    data = _load(session_id)
    todos = data.get("todos", [])
    updated = None
    for t in todos:
        if t.get("id") == todo_id:
            # 跟踪状态变化
            if payload.status is not None and t.get("status") != payload.status:
                t["previous_status"] = t.get("status")

            if payload.title is not None:
                t["title"] = payload.title
            if payload.description is not None:
                t["description"] = payload.description
            if payload.status is not None:
                t["status"] = payload.status
            if payload.priority is not None:
                t["priority"] = payload.priority
            t["updated_at"] = time.time()
            updated = Todo(**t)
            break
    if updated is not None:
        _save(session_id, data)
    return updated


def delete_todo(todo_id: str, session_id: str = "default") -> bool:
    """删除TODO

    Args:
        todo_id: TODO ID
        session_id: 会话ID，默认为"default"

    Returns:
        是否成功删除
    """
    data = _load(session_id)
    todos = data.get("todos", [])
    new_list = [t for t in todos if t.get("id") != todo_id]
    if len(new_list) == len(todos):
        return False
    # 重新整理 order
    for idx, t in enumerate(new_list):
        t["order"] = idx
    data["todos"] = new_list
    _save(session_id, data)
    return True


def reorder_todos(order: List[str], session_id: str = "default") -> List[Todo]:
    """重排TODO顺序

    Args:
        order: TODO ID列表（新顺序）
        session_id: 会话ID，默认为"default"

    Returns:
        重排后的TODO列表
    """
    data = _load(session_id)
    todos = data.get("todos", [])
    id_to_item = {t["id"]: t for t in todos}

    new_list = []
    used = set()
    for idx, tid in enumerate(order):
        if tid in id_to_item:
            item = id_to_item[tid]
            item["order"] = idx
            item["updated_at"] = time.time()
            new_list.append(item)
            used.add(tid)
    # 把未包含的追加到末尾
    for t in todos:
        if t["id"] not in used:
            t["order"] = len(new_list)
            t["updated_at"] = time.time()
            new_list.append(t)

    data["todos"] = new_list
    _save(session_id, data)
    return [Todo(**t) for t in new_list]

