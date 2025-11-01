"""报告读取工具

功能：
- 读取SearchSubAgent生成的完整报告
- 列出最近的报告
- 删除指定报告

使用场景：
- 主Agent需要查看SearchSubAgent的详细搜索结果
- 用户要求查看历史搜索报告
- 需要引用之前的搜索内容
"""
from __future__ import annotations

from typing import Any, Dict

from tools.base import BaseTool


class ReadReportTool(BaseTool):
    """读取SearchSubAgent报告工具"""

    name = "read_report"
    description = """读取SearchSubAgent生成的完整报告。

SubAgent执行完成后会返回report_id，使用此工具可查看完整的搜索结果、TODO执行记录和关键发现。

适用场景：
- 需要查看详细的搜索结果
- 需要引用之前的搜索内容
- 用户要求查看报告详情

返回格式：
- 完整的Markdown格式报告
- 包含：执行摘要、TODO记录、详细搜索结果、关键发现、附件列表

使用示例：
- read_report(report_id="20251025_143022_abc12345")
"""

    async def execute(self, report_id: str, **kwargs) -> Dict[str, Any]:
        """读取报告

        Args:
            report_id: 报告ID（由SearchSubAgent返回）

        Returns:
            {
                "error": False,
                "data": {
                    "report_id": "...",
                    "content": "完整Markdown内容"
                }
            }
        """
        try:
            from services.report_store import read_report

            content = read_report(report_id)

            if content is None:
                return {
                    "error": True,
                    "message": f"报告不存在: {report_id}",
                    "data": None
                }

            return {
                "error": False,
                "data": {
                    "report_id": report_id,
                    "content": content
                },
                "message": f"✅ 已加载报告: {report_id}"
            }

        except Exception as e:
            return {
                "error": True,
                "message": f"读取报告失败: {str(e)}",
                "data": None
            }

    def get_openai_definition(self) -> dict:
        """OpenAI工具定义"""
        return {
            "type": "function",
            "function": {
                "name": "read_report",
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "report_id": {
                            "type": "string",
                            "description": "报告ID（由SearchSubAgent返回的report_id字段）"
                        }
                    },
                    "required": ["report_id"]
                }
            }
        }


class ListReportsTool(BaseTool):
    """列出最近的报告工具"""

    name = "list_reports"
    description = """列出最近的SearchSubAgent报告。

查看最近执行的搜索任务报告列表，可以获取report_id用于读取详细内容。

返回格式：
- 报告列表（按时间倒序）
- 每个报告包含：report_id、日期、文件名、创建时间

使用示例：
- list_reports(limit=10)  # 列出最近10个报告
"""

    async def execute(self, limit: int = 10, **kwargs) -> Dict[str, Any]:
        """列出报告

        Args:
            limit: 最多返回的报告数量（默认10）

        Returns:
            {
                "error": False,
                "data": {
                    "reports": [
                        {
                            "report_id": "...",
                            "date": "...",
                            "filename": "...",
                            "created_at": ...
                        },
                        ...
                    ],
                    "total": 5
                }
            }
        """
        try:
            from services.report_store import list_reports

            reports = list_reports(limit=limit)

            return {
                "error": False,
                "data": {
                    "reports": reports,
                    "total": len(reports)
                },
                "message": f"✅ 找到 {len(reports)} 个报告"
            }

        except Exception as e:
            return {
                "error": True,
                "message": f"列出报告失败: {str(e)}",
                "data": None
            }

    def get_openai_definition(self) -> dict:
        """OpenAI工具定义"""
        return {
            "type": "function",
            "function": {
                "name": "list_reports",
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "最多返回的报告数量（默认10）",
                            "default": 10
                        }
                    }
                }
            }
        }


class DeleteReportTool(BaseTool):
    """删除报告工具"""

    name = "delete_report"
    description = """删除指定的SearchSubAgent报告。

用于清理不需要的报告文件。

⚠️ 注意：删除操作不可恢复！

使用示例：
- delete_report(report_id="20251025_143022_abc12345")
"""

    async def execute(self, report_id: str, **kwargs) -> Dict[str, Any]:
        """删除报告

        Args:
            report_id: 报告ID

        Returns:
            {
                "error": False,
                "message": "删除成功"
            }
        """
        try:
            from services.report_store import delete_report

            success = delete_report(report_id)

            if not success:
                return {
                    "error": True,
                    "message": f"报告不存在或删除失败: {report_id}",
                    "data": None
                }

            return {
                "error": False,
                "message": f"✅ 已删除报告: {report_id}",
                "data": {"report_id": report_id}
            }

        except Exception as e:
            return {
                "error": True,
                "message": f"删除报告失败: {str(e)}",
                "data": None
            }

    def get_openai_definition(self) -> dict:
        """OpenAI工具定义"""
        return {
            "type": "function",
            "function": {
                "name": "delete_report",
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "report_id": {
                            "type": "string",
                            "description": "要删除的报告ID"
                        }
                    },
                    "required": ["report_id"]
                }
            }
        }
