"""工具管理器 - 统一工具注册、描述生成和执行

参考Claude Code的MH1工具引擎设计思想
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .tavily_wrapper import (
    TavilySearchTool,
    TavilyExtractTool,
    TavilyMapTool,
    TavilyCrawlTool,
)
# Windows工具已移至SubAgent，不再直接注册
# from .windows_tools import (...)

from .todo_tools import (
    TodoListTool,
    TodoCreateTool,
    TodoUpdateTool,
    TodoDeleteTool,
    TodoReorderTool,
)
from .file_tools import (
    SaveCachedFileTool,
    ListCachedFilesTool,
    StorageStatsTool,
    CleanupStorageTool,
)
from .vision_screenshot_tools import (
    ScreenshotTool,
    ScreenshotAndAnalyzeTool,
)
from .report_tools import (
    ReadReportTool,
    ListReportsTool,
    DeleteReportTool,
)

# SubAgent工具集
from .subagent_windows import WindowsSubAgentTool
from .subagent_browser import BrowserSubAgentTool
from .subagent_search import SearchSubAgentTool  # 🆕 深度搜索SubAgent

from .base import BaseTool


class ToolManager:
    """工具管理器 - 统一管理所有工具的注册、描述和执行"""

    def __init__(self) -> None:
        self.tools: Dict[str, BaseTool] = {}
        self._register_all_tools()

    def _register_all_tools(self) -> None:
        """注册所有可用工具"""
        # Tavily工具集（4个）
        self.tools["tavily_search"] = TavilySearchTool()
        self.tools["tavily_extract"] = TavilyExtractTool()
        self.tools["tavily_map"] = TavilyMapTool()
        self.tools["tavily_crawl"] = TavilyCrawlTool()

        # Vision截图工具集（2个）
        self.tools["screenshot"] = ScreenshotTool()
        self.tools["screenshot_and_analyze"] = ScreenshotAndAnalyzeTool()

        # SubAgent工具集（3个）- 取代Windows和浏览器直接工具
        self.tools["search_subagent"] = SearchSubAgentTool()      # 🆕 深度搜索
        self.tools["windows_subagent"] = WindowsSubAgentTool()
        self.tools["browser_subagent"] = BrowserSubAgentTool()

        # ToDo管理工具集（5个）
        self.tools["list_todos"] = TodoListTool()
        self.tools["create_todo"] = TodoCreateTool()
        self.tools["update_todo"] = TodoUpdateTool()
        self.tools["delete_todo"] = TodoDeleteTool()
        self.tools["reorder_todos"] = TodoReorderTool()

        # 文件操作工具集（4个）
        self.tools["save_cached_file"] = SaveCachedFileTool()
        self.tools["list_cached_files"] = ListCachedFilesTool()
        self.tools["storage_stats"] = StorageStatsTool()
        self.tools["cleanup_storage"] = CleanupStorageTool()

        # 报告管理工具集（3个）- 用于读取SearchSubAgent报告
        self.tools["read_report"] = ReadReportTool()
        self.tools["list_reports"] = ListReportsTool()
        self.tools["delete_report"] = DeleteReportTool()

    def get_tool_descriptions(self) -> str:
        """生成工具描述列表（用于系统提示词）

        Returns:
            格式化的工具描述文本
        """
        descriptions = []
        for name, tool in self.tools.items():
            desc = f"### {name}\n{tool.description}"
            descriptions.append(desc)

        return "\n\n".join(descriptions)

    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """生成OpenAI格式的工具定义

        Returns:
            OpenAI tool格式的列表
        """
        tools = []

        # Tavily Search（轻度搜索模式）- 仅用于主Agent快速了解
        # 深度搜索请使用 search_subagent
        tools.append({
            "type": "function",
            "function": {
                "name": "tavily_search",
                "description": """【轻度搜索】快速网页搜索工具，用于主Agent快速了解基础信息。

⚠️ 注意：
- 这是【轻度搜索模式】，仅返回3条结果
- 如需深度搜索、多源对比、详细分析，请使用 search_subagent

适用场景：
- 快速查找某个概念的定义
- 获取某个技术的官网链接
- 验证某个信息的基本正确性

不适用场景（请用search_subagent）：
- 学术论文深度检索
- 技术文档全面收集
- 多源信息对比分析""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索查询词"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "返回结果数量（轻度搜索默认3条）",
                            "default": 3
                        },
                        "search_depth": {
                            "type": "string",
                            "enum": ["basic"],
                            "description": "搜索深度（轻度搜索固定为basic）",
                            "default": "basic"
                        }
                    },
                    "required": ["query"]
                }
            }
        })

        # 🔑 Tavily深度搜索工具（extract/map/crawl）已移至SearchSubAgent
        # 主Agent不再直接调用这些工具，而是通过search_subagent

        # 🔑 截图工具已移至WindowsSubAgent和BrowserSubAgent
        # 主Agent不再直接调用截图工具，而是通过windows_subagent或browser_subagent

        # SubAgent工具集 - 取代Windows和浏览器直接操控
        # Search SubAgent（深度搜索/多源对比/论文场景）
        try:
            tools.append(self.tools["search_subagent"].get_openai_definition())
        except Exception:
            # 忽略异常，避免影响其他工具注册
            pass
        # Windows SubAgent
        tools.append({
            "type": "function",
            "function": {
                "name": "windows_subagent",
                "description": """调用Windows操控SubAgent执行复杂的Windows自动化任务。

SubAgent会自动规划执行步骤（TODO），并逐步完成任务。

适用场景：
- 复杂的Windows自动化流程（如：打开应用→操作UI→保存结果）
- 多步骤操作序列
- 需要自主规划和调整的任务

SubAgent可用工具：
- launch_app: 启动应用程序
- click_element: 点击UI元素
- type_text: 输入文本
- read_file: 读取文件
- run_command: 执行系统命令
- list_processes: 列出进程
- kill_process: 终止进程
- wait_for_element: 等待元素出现
- ui_interact: UI操作序列

使用示例：
- "打开记事本并输入今天的日期"
- "检查Chrome是否在运行，如果不在则启动"
- "读取配置文件并启动对应的应用程序"
""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_description": {
                            "type": "string",
                            "description": "任务描述（详细说明要做什么），SubAgent会根据这个描述自动规划执行步骤"
                        },
                        "context": {
                            "type": "object",
                            "description": "上下文信息（可选），例如文件路径、窗口标题等"
                        }
                    },
                    "required": ["task_description"]
                }
            }
        })

        # Browser SubAgent
        tools.append({
            "type": "function",
            "function": {
                "name": "browser_subagent",
                "description": """调用浏览器操控SubAgent执行复杂的网页自动化任务。

SubAgent会自动规划执行步骤（TODO），并逐步完成任务。

适用场景：
- 复杂的网页自动化流程（如：登录→填表→提交→截图）
- 多步骤浏览器操作
- 需要自主规划和调整的网页任务

SubAgent可用工具：
- playwright_interact: 完整的浏览器交互工具
  支持26种操作：导航、点击、输入、等待、截图等

使用示例：
- "访问GitHub并搜索DeepSeek项目"
- "登录网站并填写表单"
- "抓取网页数据并保存"
""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_description": {
                            "type": "string",
                            "description": "任务描述（详细说明要做什么），SubAgent会根据这个描述自动规划执行步骤"
                        },
                        "context": {
                            "type": "object",
                            "description": "上下文信息（可选），例如URL、登录凭据等"
                        }
                    },
                    "required": ["task_description"]
                }
            }
        })

        # ToDo管理工具
        tools.append({
            "type": "function",
            "function": {
                "name": "list_todos",
                "description": "列出所有待办任务。返回任务列表，包含每个任务的id、标题、描述、状态和创建时间。",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        })

        tools.append({
            "type": "function",
            "function": {
                "name": "create_todo",
                "description": "创建新的待办任务。需要提供任务标题，可选提供描述和状态（pending/in_progress/completed）。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "任务标题"
                        },
                        "description": {
                            "type": "string",
                            "description": "任务描述（可选）"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed"],
                            "description": "任务状态，默认为pending"
                        }
                    },
                    "required": ["title"]
                }
            }
        })

        tools.append({
            "type": "function",
            "function": {
                "name": "update_todo",
                "description": "更新待办任务的信息。需要提供任务ID，可以更新标题、描述或状态。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "todo_id": {
                            "type": "string",
                            "description": "任务ID"
                        },
                        "title": {
                            "type": "string",
                            "description": "新的任务标题（可选）"
                        },
                        "description": {
                            "type": "string",
                            "description": "新的任务描述（可选）"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed"],
                            "description": "新的任务状态（可选）"
                        }
                    },
                    "required": ["todo_id"]
                }
            }
        })

        tools.append({
            "type": "function",
            "function": {
                "name": "delete_todo",
                "description": "删除指定的待办任务。需要提供任务ID。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "todo_id": {
                            "type": "string",
                            "description": "要删除的任务ID"
                        }
                    },
                    "required": ["todo_id"]
                }
            }
        })

        tools.append({
            "type": "function",
            "function": {
                "name": "reorder_todos",
                "description": "根据提供的任务ID顺序重排ToDo列表。用于调整优先级和执行顺序。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "任务ID数组，数组顺序即新的顺序"
                        }
                    },
                    "required": ["order"]
                }
            }
        })

        # 文件操作工具
        tools.append({
            "type": "function",
            "function": {
                "name": "save_cached_file",
                "description": "将缓存的文件（通过file_id引用）保存到本地路径。用于保存截图、PDF等工具生成的临时文件。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "缓存文件的ID（由截图、PDF等工具返回）"
                        },
                        "target_path": {
                            "type": "string",
                            "description": "目标保存路径，例如：'C:\\Users\\Desktop\\screenshot.png' 或 '/home/user/document.pdf'"
                        }
                    },
                    "required": ["file_id", "target_path"]
                }
            }
        })

        tools.append({
            "type": "function",
            "function": {
                "name": "list_cached_files",
                "description": "列出所有缓存的临时文件，显示file_id、类型、大小等信息。",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        })

        tools.append({
            "type": "function",
            "function": {
                "name": "storage_stats",
                "description": "查看文件存储统计信息，包括总大小、文件类型分布、最旧/最新文件等。用于监控存储使用情况。",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        })

        tools.append({
            "type": "function",
            "function": {
                "name": "cleanup_storage",
                "description": "清理旧的缓存文件以释放空间。支持按时间和大小清理。默认策略：删除30天前的文件，或当总大小超过500MB时删除最旧的文件。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "max_age_hours": {
                            "type": "integer",
                            "description": "文件最大保存时间（小时），默认720小时（30天）",
                            "default": 720
                        },
                        "max_total_size_mb": {
                            "type": "integer",
                            "description": "总大小上限（MB），默认500MB",
                            "default": 500
                        }
                    }
                }
            }
        })

        # 报告管理工具
        tools.append({
            "type": "function",
            "function": {
                "name": "read_report",
                "description": "读取SearchSubAgent生成的完整报告。SubAgent执行完成后会返回report_id，使用此工具可查看详细搜索结果、TODO记录和关键发现。",
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
        })

        tools.append({
            "type": "function",
            "function": {
                "name": "list_reports",
                "description": "列出最近的SearchSubAgent报告。查看最近执行的搜索任务，可以获取report_id用于读取详细内容。",
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
        })

        tools.append({
            "type": "function",
            "function": {
                "name": "delete_report",
                "description": "删除指定的SearchSubAgent报告。用于清理不需要的报告文件。⚠️ 注意：删除操作不可恢复！",
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
        })

        return tools

    async def execute_tool(
        self, tool_name: str, arguments: Dict[str, Any], session_id: str = "default"  # ✅ 新增：session_id参数
    ) -> Dict[str, Any]:
        """执行工具调用（带超时控制）

        Args:
            tool_name: 工具名称
            arguments: 工具参数
            session_id: 会话ID，用于TODO隔离和SubAgent上下文传递

        Returns:
            统一格式的执行结果：{"error": bool, "data": any, "message": str}
        """
        import asyncio
        import os as _os
        import logging

        logger = logging.getLogger(__name__)

        # 阶段1：工具发现与验证
        if tool_name not in self.tools:
            return {
                "error": True,
                "message": f"工具不存在: {tool_name}",
                "data": None
            }

        tool = self.tools[tool_name]

        # 阶段2：获取超时配置
        # 优先级：工具参数 > 环境变量 > 默认值（120秒）
        timeout_seconds = arguments.get("_timeout", None)
        if timeout_seconds is None:
            try:
                timeout_seconds = int(_os.getenv("TOOL_EXECUTION_TIMEOUT", "120"))
            except Exception:
                timeout_seconds = 120
        # 允许通过 0 或 负数表示“无限超时”——此处转为极大值以兼容 wait_for
        try:
            if int(timeout_seconds) <= 0:
                timeout_seconds = 10 ** 9  # 约合多年，无感知超时
        except Exception:
            pass

        # 阶段3：执行工具（带超时控制）
        try:
            logger.info(f"🔧 开始执行工具: {tool_name} (超时: {timeout_seconds}秒)")
            import time
            start_time = time.time()

            # ✅ 如果是SubAgent工具或TODO工具，自动注入session_id
            if tool_name.endswith("_subagent"):  # search_subagent, windows_subagent, browser_subagent
                if "session_id" not in arguments:
                    arguments["session_id"] = session_id
                    logger.info(f"✅ 自动注入session_id给SubAgent: {session_id}")
            elif tool_name in ["list_todos", "create_todo", "update_todo", "delete_todo", "reorder_todos"]:  # TODO工具
                if "session_id" not in arguments:
                    arguments["session_id"] = session_id
                    logger.info(f"✅ 自动注入session_id给TODO工具: {session_id}")

            # 使用 asyncio.wait_for 添加超时保护
            result = await asyncio.wait_for(
                tool.execute(**arguments),
                timeout=timeout_seconds
            )

            elapsed = time.time() - start_time
            logger.info(f"✅ 工具执行完成: {tool_name} ({elapsed:.2f}秒)")

            return result

        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            logger.error(f"⏰ 工具执行超时: {tool_name} ({elapsed:.2f}秒 / {timeout_seconds}秒)")
            return {
                "error": True,
                "message": f"工具执行超时 ({timeout_seconds}秒): {tool_name}。建议检查网络连接或增加超时时间。",
                "data": None
            }

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ 工具执行异常: {tool_name} ({elapsed:.2f}秒) - {str(e)}")
            return {
                "error": True,
                "message": f"工具执行异常: {e}",
                "data": None
            }

    async def execute_tool_calls(
        self, tool_calls: List[Dict[str, Any]], session_id: str = "default"  # ✅ 新增：session_id参数
    ) -> List[Dict[str, Any]]:
        """批量执行工具调用（限流并发）

        - 使用 asyncio.Semaphore 控制最大并发数
        - 通过 env `MAX_TOOL_CONCURRENCY` 配置并发度（默认 5）
        - 返回顺序与传入的 tool_calls 顺序一致
        - session_id: 会话ID，用于TODO隔离和SubAgent上下文传递
        """
        import asyncio
        import os as _os

        try:
            # 为降低外部 API 压力，将并发默认值从 5 下调到 1（可通过环境变量覆盖）
            max_c = int(_os.getenv("MAX_TOOL_CONCURRENCY", "1"))
            if max_c <= 0:
                max_c = 1
        except Exception:
            max_c = 5

        sem = asyncio.Semaphore(max_c)

        async def run_one(tool_call: Dict[str, Any]) -> Dict[str, Any]:
            tool_id = tool_call.get("id", "unknown")
            function = tool_call.get("function", {})
            tool_name = function.get("name")
            arguments_str = function.get("arguments", "{}")

            # 解析参数
            try:
                arguments = json.loads(arguments_str)
            except json.JSONDecodeError:
                return {
                    "tool_call_id": tool_id,
                    "role": "tool",
                    "content": json.dumps({
                        "error": True,
                        "message": "参数解析失败：无效的JSON格式"
                    }, ensure_ascii=False)
                }

            async with sem:
                result = await self.execute_tool(tool_name, arguments, session_id=session_id)  # ✅ 传递session_id

            return {
                "tool_call_id": tool_id,
                "role": "tool",
                "name": tool_name,
                "content": json.dumps(result, ensure_ascii=False)
            }

        tasks = [run_one(tc) for tc in tool_calls]
        return await asyncio.gather(*tasks)


# 全局单例
tool_manager = ToolManager()
