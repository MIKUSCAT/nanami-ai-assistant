"""
记忆与上下文管理（简化实现）

特性：
- 短期记忆：当前会话消息
- 中期记忆：当上下文超过阈值（92%）时用主模型生成摘要并替换早期消息
- 对话持久化：自动保存对话历史到文件系统（data/conversations/）
- 无长期存储与权限校验，符合"去安全复杂性"的要求

参考思想：Kode-main 的 autoCompactCore（阈值与摘要策略）
"""
from __future__ import annotations

import os
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .model_manager import model_manager


# 对话持久化目录
CONVERSATION_DIR = os.path.join(os.getcwd(), "data", "conversations")


def _ensure_conversation_dir() -> None:
    """确保对话目录存在"""
    os.makedirs(CONVERSATION_DIR, exist_ok=True)


def _save_conversation_to_disk(session_id: str, messages: List[Dict[str, Any]],
                               mid_term_summary: Optional[str] = None) -> None:
    """保存对话到磁盘

    Args:
        session_id: 会话ID
        messages: 对话消息列表
        mid_term_summary: 中期摘要（如果有）
    """
    _ensure_conversation_dir()

    conversation_data = {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "mid_term_summary": mid_term_summary,
        "messages": messages
    }

    file_path = os.path.join(CONVERSATION_DIR, f"{session_id}.json")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(conversation_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ 保存对话失败: {e}")


def _load_conversation_from_disk(session_id: str) -> Optional[Dict[str, Any]]:
    """从磁盘加载对话

    Args:
        session_id: 会话ID

    Returns:
        对话数据字典，如果不存在则返回None
    """
    file_path = os.path.join(CONVERSATION_DIR, f"{session_id}.json")

    if not os.path.exists(file_path):
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ 加载对话失败: {e}")
        return None


def _get_auto_compact_ratio() -> float:
    """从环境变量读取压缩阈值，默认 0.92。

    仅在调用时读取，避免导入顺序导致 .env 未加载。
    """
    try:
        val = float(os.getenv("AUTO_COMPACT_RATIO", "0.92"))
        # 基本合理性保护：范围不合法则回退默认
        if not (0.0 < val < 1.0):
            return 0.92
        return val
    except Exception:
        return 0.92


def _estimate_tokens(messages: List[Dict[str, Any]]) -> int:
    total_chars = 0
    for m in messages:
        c = m.get("content", "")
        if isinstance(c, str):
            total_chars += len(c)
        else:
            total_chars += len(str(c))
    return max(1, total_chars // 4)


class MemoryManager:
    def __init__(self, session_id: Optional[str] = None, load_history: bool = False) -> None:
        """初始化记忆管理器

        Args:
            session_id: 会话ID，如果为None则生成新ID
            load_history: 是否加载历史对话（如果存在）
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.short_term_memory: List[Dict[str, Any]] = []
        self.mid_term_summary: str | None = None

        # 尝试加载历史对话
        if load_history and session_id:
            conversation_data = _load_conversation_from_disk(session_id)
            if conversation_data:
                self.short_term_memory = conversation_data.get("messages", [])
                self.mid_term_summary = conversation_data.get("mid_term_summary")

    def load_messages(self, messages: List[Dict[str, Any]]) -> None:
        self.short_term_memory.extend(messages)

    def add_message(self, message: Dict[str, Any]) -> None:
        self.short_term_memory.append(message)

    def get_context(self) -> List[Dict[str, Any]]:
        ctx: List[Dict[str, Any]] = []
        if self.mid_term_summary:
            ctx.append({"role": "system", "content": f"会话摘要：\n{self.mid_term_summary}"})
        ctx.extend(self.short_term_memory)
        return ctx

    def save_to_disk(self) -> None:
        """保存当前对话到磁盘"""
        _save_conversation_to_disk(
            self.session_id,
            self.short_term_memory,
            self.mid_term_summary
        )

    async def check_and_compact(self) -> Dict[str, Any]:
        messages = self.get_context()
        tokens = _estimate_tokens(messages)
        main_profile = model_manager.get_profile("main")
        ratio = _get_auto_compact_ratio()
        threshold = int(main_profile.context_length * ratio)
        if tokens < threshold:
            return {"compacted": False, "tokens": tokens, "threshold": threshold}

        prompt = (
            "请根据当前对话生成结构化中文摘要，保留：项目背景/关键信息/已完成/待办/注意事项，"
            "用于继续协作。输出应简洁、要点化。"
        )
        # 使用压缩模型进行摘要
        client = model_manager.get_model("compact")
        resp = await client.chat(messages + [{"role": "user", "content": prompt}])
        summary = resp.get("content") if isinstance(resp, dict) else str(resp)
        if not summary:
            summary = "(自动压缩失败：未能生成摘要)"

        self.mid_term_summary = summary
        self.short_term_memory = self.short_term_memory[-6:]

        # 保存压缩后的对话
        self.save_to_disk()

        return {"compacted": True, "tokens": tokens, "threshold": threshold}
