"""长期记忆（Markdown 持久化）

设计目标：
- 使用模型从对话中提炼稳定偏好/长期事实，并以 Markdown 形式持久化
- 默认按开关启用，便于控制成本与行为
- 不引入向量库与复杂安全机制，保持最小可用

环境变量：
- LTM_MD_ENABLED: 是否启用模型提炼与写入（"1" 启用，默认 "0" 关闭）
- LTM_MD_PATH: Markdown 文件路径，默认 data/ltm.md
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ltm_md_enabled() -> bool:
    return os.getenv("LTM_MD_ENABLED", "0") == "1"


def ltm_md_path() -> str:
    path = os.getenv("LTM_MD_PATH") or os.path.join(os.getcwd(), "data", "ltm.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


class LTMMarkdown:
    """Markdown 形式的长期记忆存储"""

    def __init__(self, path: Optional[str] = None) -> None:
        self.path = path or ltm_md_path()
        # 如果文件不存在，写入标题
        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as f:
                f.write("# 长期记忆库\n\n")

    def append_section(self, title: str, content: str, tags: Optional[List[str]] = None) -> None:
        """追加一个带时间戳的小节"""
        tags_str = ", ".join(tags or [])
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(f"### [{_ts()}] {title}\n\n")
            if tags_str:
                f.write(f"- Tags: {tags_str}\n\n")
            f.write(content.strip() + "\n\n")

    def read_all(self) -> str:
        """读取完整的长期记忆内容

        Returns:
            完整的Markdown文本，如果文件不存在则返回空字符串
        """
        if not os.path.exists(self.path):
            return ""
        with open(self.path, "r", encoding="utf-8") as f:
            return f.read()

    def read_recent_sections(self, n: int = 3, tag_filter: Optional[str] = None) -> str:
        """读取最近N个小节

        Args:
            n: 返回最近的N个小节
            tag_filter: 如果指定，只返回包含该标签的小节（如"preference"）

        Returns:
            最近N个小节的Markdown文本
        """
        content = self.read_all()
        if not content:
            return ""

        # 按 ### 分割小节（跳过第一个标题）
        sections = content.split("### ")[1:]  # [0]是"# 长期记忆库\n\n"

        # 如果有标签过滤
        if tag_filter:
            filtered = []
            for s in sections:
                if f"Tags: {tag_filter}" in s or f"Tags: preference" in s:
                    filtered.append(s)
            sections = filtered

        # 取最近N个
        recent = sections[-n:] if len(sections) > n else sections

        # 重新组合为Markdown
        if not recent:
            return ""
        return "### " + "\n\n### ".join(recent)

    async def summarize_preferences(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        """使用主模型从对话中提炼"用户偏好/沟通与输出习惯"等长期信息（中文要点列举）

        改进：在总结前会先读取已有的LTM内容，基于已有记忆进行增量式总结，避免重复
        """
        try:
            from .model_manager import model_manager

            client = model_manager.get_model("main")

            # 读取已有的长期记忆
            existing_ltm = self.read_all()

            # 构建prompt，如果有已有记忆，则让AI在此基础上增量更新
            if existing_ltm and existing_ltm.strip() and existing_ltm.strip() != "# 长期记忆库":
                prompt = (
                    "## 已有的长期记忆\n\n"
                    f"{existing_ltm}\n\n"
                    "---\n\n"
                    "## 任务\n\n"
                    "请先仔细阅读上面的已有长期记忆，然后基于当前对话，提炼用户长期稳定的偏好与习惯（非一次性需求）。\n\n"
                    "要求：\n"
                    "- 用中文要点列举（每条≤30字）\n"
                    "- 尽量聚焦沟通风格、输出格式偏好、常用技术栈/平台、常用工具、响应习惯等\n"
                    "- **重要：在已有记忆的基础上进行增量更新，避免重复已记录的内容**\n"
                    "- 如果当前对话没有新的长期偏好信息，或者所有偏好已在记忆中，可以返回空字符串\n"
                    "- 避免冗长与一次性上下文细节\n"
                )
            else:
                # 如果是第一次总结，使用原有的prompt
                prompt = (
                    "请基于以上对话，提炼用户长期稳定的偏好与习惯（非一次性需求）。\n"
                    "要求：\n"
                    "- 用中文要点列举（每条≤30字）\n"
                    "- 尽量聚焦沟通风格、输出格式偏好、常用技术栈/平台、常用工具、响应习惯等\n"
                    "- 避免冗长与一次性上下文细节\n"
                )

            resp = await client.chat(messages + [{"role": "user", "content": prompt}])
            return resp.get("content") if isinstance(resp, dict) else str(resp)
        except Exception:
            return None

