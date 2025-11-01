"""
深度搜索SubAgent - 专门处理网络信息深度收集任务

功能：
- 集成Tavily工具集（搜索、提取、映射、爬取）
- TODO LIST规划：分解复杂搜索任务为多个子查询
- 自主策略调整：根据搜索结果动态优化查询
- 结构化报告：生成紧凑的搜索结果摘要

使用场景：
- 学术论文深度检索
- 技术文档全面收集
- 多源信息对比分析
- 深度主题研究

优化改进：
- 精简系统提示词，提高遵循率
- 强制置信度标注和URL验证
- 要求交叉验证和来源可靠性检查
- 区分"验证事实"vs"推测内容"
"""
from __future__ import annotations

from typing import Any, Dict

from core.subagent import SubAgent
from tools.tavily_wrapper import (
    TavilySearchTool,
    TavilyExtractTool,
    TavilyMapTool,
    TavilyCrawlTool
)
from tools.base import BaseTool


class SearchSubAgent(SubAgent):
    """深度搜索SubAgent

    专门处理网络信息深度收集，具备：
    - Tavily完整工具集
    - TODO规划能力
    - 多轮搜索策略
    - 反幻觉机制
    """

    def _get_system_prompt(self) -> str:
        """精简系统提示词：强约束反幻觉 + TODO复用机制

        核心改进：
        - 精简提示词，提高遵循率
        - 强制置信度标注
        - 要求来源URL和交叉验证
        - 明确"推测"vs"验证事实"
        - 智能复用现有TODO，避免重复创建
        """
        tool_descriptions = self._get_tool_descriptions()
        return (
            "你是【深度搜索采集】专家SubAgent。\n\n"
            "📋 执行流程：\n"
            "1. 🔍 **检查现有TODO**：尝试调用 create_subagent_todo\n"
            "   - 如果系统提示'跳过创建新TODO'，说明已有活跃任务，直接继续执行\n"
            "   - 如果没有活跃TODO，系统会创建新TODO后再继续\n"
            "2. 调用 tavily_search/tavily_extract/tavily_map/tavily_crawl 完成检索\n"
            "3. 每完成一个任务立即使用 update_subagent_todo 更新状态\n\n"
            "🔍 搜索参数要求：\n"
            "- search_depth=advanced（禁止使用basic）\n"
            "- max_results=10-15\n"
            "- include_domains 锁定权威来源（arXiv、GitHub、官网等）\n\n"
            "⚠️ 反幻觉硬规则：\n"
            "- 任何关键声明必须附带URL或标注【推测】\n"
            "- 核心发现需至少2个独立来源验证\n"
            "- 对每条发现标注置信度：[高/中/低]\n"
            "- 无法验证的信息必须明确标记【待验证】\n\n"
            "📝 输出格式：\n"
            "```\n"
            "## 摘要（≤200字）\n"
            "## 关键发现（5-10条）\n"
            "- [高置信度] 发现1 + URL + 验证来源数\n"
            "- [中置信度] 发现2 + URL + 验证来源数\n"
            "- [低置信度] 发现3 + URL + 验证来源数\n"
            "- [推测] 发现4 + 无URL或需进一步验证\n"
            "## 来源列表\n"
            "包含URL、标题、发布时间/检索时间\n"
            "```\n\n"
            "可用工具：\n" + tool_descriptions + "\n\n"
            "❌ 禁止：重复创建TODO、仅输出文字不调用工具、使用basic搜索、遗忘URL标注"
        )

    def __init__(self, max_iterations: int = 999, model_pointer: str = "search_agent", session_id: str = "default"):
        self.model_pointer = model_pointer
        self.session_id = session_id  # 保存session_id供后续使用
        super().__init__(
            name="SearchSubAgent",
            description="深度搜索专家，负责学术论文、技术文档、新闻资讯的全面收集和分析",
            system_prompt=None,
            max_iterations=max_iterations,
            model_pointer=model_pointer,
            session_id=session_id
        )

    def _has_active_search_todos(self, task_description: str) -> bool:
        """检查是否有未完成的search类型TODO

        检查是否存在与当前任务相关的未完成TODO，避免重复创建

        Args:
            task_description: 当前任务描述

        Returns:
            True if存在未完成的search TODO，False otherwise
        """
        try:
            from services.todo_store import list_todos

            todos = list_todos(session_id=self.session_id)

            # 检查是否有search类型且未完成的TODO
            active_todos = [
                t for t in todos
                if t.agent_type == "search"
                and t.status in ["pending", "in_progress"]
            ]

            # 如果没有活跃的search TODO，返回False
            if not active_todos:
                return False

            # 简单关键词匹配：如果TODO标题包含任务关键词，认为是相关任务
            task_keywords = set(task_description.lower().split()[:5])  # 取前5个关键词

            for todo in active_todos:
                todo_keywords = set(todo.title.lower().split())
                # 如果关键词重叠度超过50%，认为是同一任务
                if len(task_keywords & todo_keywords) >= max(1, len(task_keywords) * 0.5):
                    return True

            return False
        except Exception:
            # 如果检查失败，假设没有活跃TODO，继续创建新的
            return False

    def _register_tools(self):
        """注册Tavily工具集

        包括：
        - tavily_search: 深度搜索
        - tavily_extract: URL内容提取
        - tavily_map: 网站结构映射
        - tavily_crawl: 深度爬取
        """
        self.tools["tavily_search"] = TavilySearchTool()
        self.tools["tavily_extract"] = TavilyExtractTool()
        self.tools["tavily_map"] = TavilyMapTool()
        self.tools["tavily_crawl"] = TavilyCrawlTool()

    async def _generate_compact_report(self, final_content: str, iterations: int) -> Dict[str, Any]:
        """生成紧凑报告并保存完整报告到磁盘

        重写父类方法，添加报告保存功能

        Args:
            final_content: 最终输出内容
            iterations: 当前迭代次数

        Returns:
            紧凑版报告 + report_id
        """
        base_report = await super()._generate_compact_report(final_content, iterations)

        search_results = []
        for msg in self.memory.get_context():
            if msg.get("role") == "tool" and msg.get("name") in ["tavily_search", "tavily_extract", "tavily_map", "tavily_crawl"]:
                try:
                    import json
                    content = json.loads(msg.get("content", "{}"))
                    search_results.append({
                        "tool": msg.get("name"),
                        "data": content.get("data", {})
                    })
                except Exception:
                    pass

        from services.todo_store import list_todos
        all_todos = list_todos(session_id=self.session_id)
        subagent_todos = [
            {
                "title": t.title,
                "description": t.description,
                "status": t.status,
                "priority": t.priority
            }
            for t in all_todos
            if t.agent_type == "search"
        ]

        try:
            from services.report_store import save_report

            report_id = save_report(
                task_description="SearchSubAgent execution",
                summary=base_report.get("summary", ""),
                todos=subagent_todos,
                search_results=search_results,
                key_findings=base_report.get("key_findings", []),
                artifacts=base_report.get("artifacts", []),
                iterations=iterations,
                metadata={
                    "subagent": self.name,
                    "max_iterations": self.max_iterations,
                    "todos_completed": base_report.get("todos_completed", 0),
                    "todos_total": base_report.get("todos_total", 0)
                }
            )

            base_report["report_id"] = report_id
            base_report["message"] = f"✅ 深度搜索完成！报告已保存: {report_id}"

        except Exception as e:
            import logging
            logging.error(f"保存报告失败: {str(e)}")
            base_report["report_save_error"] = str(e)

        return base_report


class SearchSubAgentTool(BaseTool):
    """SearchSubAgent调用工具 - 主Agent使用此工具调用SearchSubAgent

    这是主Agent和SearchSubAgent之间的桥梁
    """

    name = "search_subagent"
    description = """【必须使用】学术论文/技术文档全面收集。

✅ 必须使用场景：
- 学术论文检索（arXiv/Scholar）
- 技术文档全面收集（≥5 个权威来源）
- 多源信息对比与可信度评估
- 需要锁定官网、官方博客、GitHub 官方仓库等权威渠道

❌ 禁止使用场景：
- 快速查询基础概念（请直接用 tavily_search）
- 仅需 1-3 条结果或不需要深度分析

SubAgent 会自动：
1. 规划并持续更新 TODO
2. 使用 tavily_search / tavily_map / tavily_crawl / tavily_extract 的 advanced 模式采集权威信息
3. 结合 include_domains 锁定官方与知名站点并进行交叉验证
4. 生成结构化报告（含来源、时间、可信度与后续建议）
"""

    async def execute(self, task_description: str, context: Dict[str, Any] = None, session_id: str = "default", **kwargs) -> Dict[str, Any]:
        """执行深度搜索

        Args:
            task_description: 详细的搜索任务描述
                应包括：搜索主题、关键词、期望深度、权威来源要求
            context: 上下文信息（可选）
            session_id: 会话ID，用于TODO隔离
            **kwargs: 其他参数

        Returns:
            紧凑的结构化搜索报告
        """
        subagent = SearchSubAgent(session_id=session_id)
        result = await subagent.execute(task_description, context)
        return result

    def get_openai_definition(self) -> dict:
        """OpenAI工具定义"""
        return {
            "type": "function",
            "function": {
                "name": "search_subagent",
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_description": {
                            "type": "string",
                            "description": """详细的搜索任务描述。

建议包括以下信息：
1. **搜索主题**：明确的研究主题或问题
2. **关键词**：核心关键词和相关术语
3. **权威来源**：期望的权威网站（如arXiv、GitHub、官方文档）
4. **信息深度**：需要摘要还是详细内容
5. **时效性**：是否需要最新信息（如：过去7天）

示例：
"在arXiv.org上搜索DeepSeek R1相关论文，重点关注模型架构和训练方法，需要详细的技术内容"

"收集Python FastAPI的官方文档、GitHub示例和Stack Overflow常见问题，需要全面覆盖"
"""
                        },
                        "context": {
                            "type": "object",
                            "description": "上下文信息（可选）。可以包含之前的搜索结果、用户偏好等"
                        },
                        "session_id": {
                            "type": "string",
                            "description": "会话ID，用于TODO隔离（由主Agent传递）"
                        }
                    },
                    "required": ["task_description"]
                }
            }
        }
