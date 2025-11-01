"""
SubAgent架构 - 参考Claude Code的I2A函数设计，集成TODO规划能力

核心特性：
1. **TODO规划能力**：SubAgent能够自己分解任务、规划执行步骤
2. **工具注册机制**：类似主Agent的tool_manager，支持动态注册工具
3. **隔离执行环境**：独立的Agent实例、专用工具集、隔离权限
4. **自主任务管理**：自动创建、更新、完成TODO项

设计理念：
- SubAgent = 主Agent的微缩版，完整的规划和执行能力
- 类似Claude Code的Task工具 + I2A实例化函数
- 每个SubAgent有自己的TODO列表和工具集
- SubAgent执行完成后返回单一结果给主Agent
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from core.model_manager import model_manager
from core.memory import MemoryManager

logger = logging.getLogger(__name__)


class SubAgent:
    """SubAgent基类 - 具备TODO规划能力的隔离Agent

    特性：
    - 独立的Agent循环实例
    - 集成TODO LIST，能自主规划任务
    - 工具注册机制（预留接口）
    - 隔离的执行环境和权限
    """

    def __init__(
        self,
        name: str,
        description: str,
        system_prompt: str = "",  # 预留：具体提示词由子类定义
        max_iterations: int = 15,
        model_pointer: str = "task",  # 默认使用task模型，子类可覆盖
        session_id: str = "default"  # ✅ 新增：session_id参数
    ):
        """
        Args:
            name: SubAgent名称
            description: SubAgent描述
            system_prompt: 系统提示词（预留，默认空）
            max_iterations: 最大迭代次数
            model_pointer: 模型指针（可由子类传入独立配置）
            session_id: 会话ID，用于TODO隔离
        """
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.model_pointer = model_pointer  # 支持每个SubAgent使用独立模型
        self.session_id = session_id  # ✅ 保存session_id
        self.memory = MemoryManager()

        # 工具注册表（预留接口）
        self.tools: Dict[str, Any] = {}
        self._register_tools()

    def _register_tools(self):
        """注册SubAgent专用工具

        预留方法：由子类实现具体工具注册
        子类应该在这里注册自己的专用工具，例如：

        class WindowsSubAgent(SubAgent):
            def _register_tools(self):
                self.tools["launch_app"] = WindowsLaunchAppTool()
                self.tools["click_element"] = WindowsClickElementTool()
                # ... 更多工具
        """
        pass  # 预留：子类实现

    def _get_tool_descriptions(self) -> str:
        """生成工具描述（用于系统提示词）"""
        if not self.tools:
            return "（当前无可用工具）"

        descriptions = []
        for name, tool in self.tools.items():
            desc = f"### {name}\n{tool.description if hasattr(tool, 'description') else '无描述'}"
            descriptions.append(desc)
        return "\n\n".join(descriptions)

    def _get_openai_tools(self) -> List[Dict[str, Any]]:
        """生成OpenAI格式的工具定义"""
        openai_tools = []

        # 添加SubAgent的专用工具
        for name, tool in self.tools.items():
            if hasattr(tool, 'get_openai_definition'):
                openai_tools.append(tool.get_openai_definition())

        # 添加TODO管理工具（SubAgent内置）
        openai_tools.extend([
            {
                "type": "function",
                "function": {
                    "name": "create_subagent_todo",
                    "description": "创建SubAgent任务清单。用于规划任务执行步骤。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "todos": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string", "description": "任务标题"},
                                        "description": {"type": "string", "description": "任务描述"}
                                    },
                                    "required": ["title"]
                                }
                            }
                        },
                        "required": ["todos"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_subagent_todo",
                    "description": "更新SubAgent任务状态。任务完成后标记为completed。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "index": {"type": "integer", "description": "任务索引（从0开始）"},
                            "status": {
                                "type": "string",
                                "enum": ["pending", "in_progress", "completed"],
                                "description": "新状态"
                            }
                        },
                        "required": ["index", "status"]
                    }
                }
            }
        ])

        return openai_tools

    def _get_system_prompt(self) -> str:
        """生成SubAgent的系统提示词"""
        tool_descriptions = self._get_tool_descriptions()

        # 如果子类提供了自定义提示词，使用自定义的
        if self.system_prompt:
            return self.system_prompt.format(
                name=self.name,
                description=self.description,
                tool_descriptions=tool_descriptions
            )

        # 默认提示词（预留框架）
        return f"""你是一个专门的SubAgent，负责执行特定任务。

**你的角色**: {self.description}

**可用工具**:
{tool_descriptions}

**任务执行流程**:
1. 使用 `create_subagent_todo` 规划任务步骤
2. 逐步执行每个TODO，使用专用工具
3. 使用 `update_subagent_todo` 更新任务状态
4. 完成所有任务后，总结执行结果

**重要提示**:
- 你必须先规划TODO，再执行任务
- 每完成一个步骤，立即更新TODO状态
- 遇到问题时，说明具体原因并调整计划
- 执行环境是隔离的，只能使用上述工具
"""

    async def _generate_compact_report(self, final_content: str, iterations: int) -> Dict[str, Any]:
        """生成紧凑的结构化报告（核心优化）

        设计理念：
        - SubAgent的执行细节（memory、截图、工具调用历史）不传回主Agent
        - 仅返回紧凑的结构化报告：摘要、关键发现、附件ID
        - 大型数据（截图）缓存到file_store，仅传file_id

        Returns:
            紧凑的结构化报告：
            {
                "error": False,
                "summary": "执行摘要（200字以内）",
                "key_findings": ["发现1", "发现2", ...],
                "artifacts": ["file_id1", "file_id2"],  # 截图等文件的ID
                "todos_completed": 8,
                "todos_total": 10,
                "iterations": 5,
                "subagent": "WindowsSubAgent"
            }
        """
        try:
            # 兜底修复：若最后一轮模型未显式将最后一步标记为 completed，这里自动完成进行中的步骤
            # 仅将 in_progress 标记为 completed；pending 视为未开始，不强制完成
            try:
                if hasattr(self, "todos") and isinstance(self.todos, list):
                    from services.todo_store import update_todo
                    from schemas.todo import TodoUpdate

                    for i, t in enumerate(self.todos):
                        if isinstance(t, dict) and t.get("status") == "in_progress" and t.get("_todo_id"):
                            self.todos[i]["status"] = "completed"
                            try:
                                update_todo(t["_todo_id"], TodoUpdate(status="completed"), session_id=self.session_id)
                            except Exception:
                                # 忽略持久化失败，继续生成报告
                                pass
            except Exception:
                # 忽略兜底逻辑异常
                pass
            from services.file_store import cache_base64_data
            import base64

            # 1. 提取关键发现（从memory中收集）
            key_findings = []
            artifacts = []

            # 遍历memory，收集工具执行结果
            for msg in self.memory.get_context():
                if msg.get("role") == "tool":
                    try:
                        tool_result = json.loads(msg.get("content", "{}"))
                        if not tool_result.get("error", False):
                            data = tool_result.get("data", {})

                            # 提取关键发现
                            if isinstance(data, dict):
                                # 检查是否有file_id（截图等）
                                if "file_id" in data:
                                    artifacts.append(data["file_id"])

                                # 检查是否有screenshot_file_id
                                if "screenshot_file_id" in data:
                                    artifacts.append(data["screenshot_file_id"])

                                # 提取摘要信息
                                if "_summary" in data:
                                    key_findings.append(data["_summary"])
                    except Exception:
                        continue

            # 2. 统计TODO完成情况
            todos_completed = len([t for t in self.todos if t.get("status") == "completed"]) if hasattr(self, "todos") else 0
            todos_total = len(self.todos) if hasattr(self, "todos") else 0

            # 3. 生成简洁摘要（使用quick模型）
            # 如果final_content太长，截断到500字并生成摘要
            summary = final_content
            if len(final_content) > 500:
                # 使用quick模型生成摘要
                try:
                    quick_client = model_manager.get_model("quick")
                    summary_resp = await quick_client.chat([
                        {
                            "role": "user",
                            "content": f"请用200字以内总结以下SubAgent执行结果：\n\n{final_content[:2000]}"
                        }
                    ])
                    summary = summary_resp.get("content", final_content[:200])
                except Exception as e:
                    logger.warning(f"摘要生成失败，使用截断: {e}")
                    summary = final_content[:200] + "..."

            # 4. 返回紧凑报告
            return {
                "error": False,
                "summary": summary,
                "key_findings": key_findings[:10],  # 最多10条关键发现
                "artifacts": list(set(artifacts)),  # 去重
                "todos_completed": todos_completed,
                "todos_total": todos_total,
                "iterations": iterations,
                "subagent": self.name
            }

        except Exception as e:
            logger.error(f"生成紧凑报告失败: {e}")
            # 降级处理：返回简化版报告
            return {
                "error": False,
                "summary": final_content[:200] if final_content else "SubAgent执行完成",
                "key_findings": [],
                "artifacts": [],
                "todos_completed": len([t for t in self.todos if t.get("status") == "completed"]),
                "todos_total": len(self.todos),
                "iterations": iterations,
                "subagent": self.name
            }

    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """执行SubAgent工具

        包括：
        1. SubAgent专用工具（由子类注册）
        2. SubAgent内置工具（TODO管理）
        """
        try:
            # 处理TODO管理工具
            if tool_name == "create_subagent_todo":
                from services.todo_store import create_todo, list_todos
                from schemas.todo import TodoCreate, TodoPriority, TodoAgentType

                # 特殊处理：SearchSubAgent检查是否已有活跃TODO，避免重复创建
                if self.name == "SearchSubAgent":
                    try:
                        existing_todos = list_todos(session_id=self.session_id)
                        active_search_todos = [
                            t for t in existing_todos
                            if t.agent_type == "search"
                            and t.status in ["pending", "in_progress"]
                        ]

                        if active_search_todos:
                            # 将现有TODO加载到self.todos中，供update_subagent_todo使用
                            self.todos = [
                                {
                                    "title": t.title.replace("[SearchSubAgent] ", ""),  # 移除前缀便于显示
                                    "description": t.description,
                                    "status": t.status.value,
                                    "_todo_id": t.id  # 保存真实ID用于更新
                                }
                                for t in active_search_todos
                            ]

                            # 返回现有TODO信息，让SearchSubAgent继续执行
                            return {
                                "error": False,
                                "message": f"检测到{len(active_search_todos)}个未完成的search任务，跳过创建新TODO。请继续执行现有任务。",
                                "data": {
                                    "skipped": True,
                                    "active_todos_count": len(active_search_todos),
                                    "existing_todos": self.todos
                                }
                            }
                    except Exception:
                        # 如果检查失败，继续创建TODO
                        pass

                agent_type_mapping = {
                    "SearchSubAgent": TodoAgentType.search,
                    "BrowserSubAgent": TodoAgentType.browser,
                    "WindowsSubAgent": TodoAgentType.windows,
                }
                agent_type = agent_type_mapping.get(self.name, TodoAgentType.custom)

                todos = arguments.get("todos", [])
                self.todos = [
                    {
                        "title": t.get("title", ""),
                        "description": t.get("description", ""),
                        "status": "pending"
                    }
                    for t in todos
                ]

                for t in self.todos:
                    created = create_todo(
                        TodoCreate(
                            title=f"[{self.name}] {t['title']}",
                            description=t['description'],
                            status="pending",
                            priority=TodoPriority.medium,
                            agent_type=agent_type
                        ),
                        session_id=self.session_id
                    )
                    t["_todo_id"] = created.id

                return {
                    "error": False,
                    "data": {
                        "todos": self.todos,
                        "message": f"✅ 已创建 {len(self.todos)} 个任务并持久化到存储"
                    }
                }

            elif tool_name == "update_subagent_todo":
                from services.todo_store import update_todo
                from schemas.todo import TodoUpdate

                index = arguments.get("index", 0)
                status = arguments.get("status", "pending")

                if 0 <= index < len(self.todos):
                    self.todos[index]["status"] = status

                    # ✅ 同步更新到主存储（传递session_id）
                    if "_todo_id" in self.todos[index]:
                        update_todo(
                            self.todos[index]["_todo_id"],
                            TodoUpdate(status=status),
                            session_id=self.session_id  # ✅ 传递session_id
                        )

                    return {
                        "error": False,
                        "data": {
                            "todo": self.todos[index],
                            "message": f"✅ 任务 #{index} 状态更新为 {status}并已持久化"
                        }
                    }
                else:
                    return {
                        "error": True,
                        "message": f"任务索引 {index} 超出范围"
                    }

            # 处理SubAgent专用工具
            elif tool_name in self.tools:
                tool = self.tools[tool_name]
                result = await tool.execute(**arguments)
                return result

            else:
                return {
                    "error": True,
                    "message": f"工具不存在: {tool_name}"
                }

        except Exception as e:
            import traceback
            logger.error(f"工具执行异常: {tool_name} - {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "error": True,
                "message": f"工具执行异常: {str(e)}"
            }

    async def execute(self, task_description: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行SubAgent任务

        Args:
            task_description: 任务描述（详细的执行指令）
            context: 上下文信息（可选）

        Returns:
            执行结果：{"error": bool, "data": any, "message": str}
        """
        try:
            logger.info(f"🤖 SubAgent [{self.name}] 开始执行任务")

            # 初始化TODO列表
            self.todos: List[Dict[str, Any]] = []

            # ✅ 从主存储加载该SubAgent的TODO（按session_id隔离）
            from services.todo_store import list_todos
            from schemas.todo import TodoAgentType

            # 映射SubAgent名称到AgentType
            agent_type_mapping = {
                "SearchSubAgent": TodoAgentType.search,
                "BrowserSubAgent": TodoAgentType.browser,
                "WindowsSubAgent": TodoAgentType.windows,
            }

            agent_type = agent_type_mapping.get(self.name, TodoAgentType.custom)

            # ✅ 传递session_id加载TODO
            existing_todos = list_todos(session_id=self.session_id)
            subagent_todos = [
                t for t in existing_todos
                if t.agent_type == agent_type and t.status in ["pending", "in_progress"]
            ]

            if subagent_todos:
                logger.info(f"✅ 检测到 {len(subagent_todos)} 个未完成的{self.name}TODO，准备继续执行")
                # 转换为 SubAgent 的内部格式
                self.todos = [
                    {
                        "title": t.title,
                        "description": t.description or "",
                        "status": t.status,
                        "_todo_id": t.id  # 保存ID用于后续更新
                    }
                    for t in subagent_todos
                ]

            # 1. 注入系统提示
            system_prompt = self._get_system_prompt()
            self.memory.add_message({"role": "system", "content": system_prompt})

            # 2. 注入上下文信息（如果有）
            if context:
                context_str = json.dumps(context, ensure_ascii=False, indent=2)
                self.memory.add_message({
                    "role": "system",
                    "content": f"**上下文信息**:\n```json\n{context_str}\n```"
                })

            # 3. 添加任务描述
            self.memory.add_message({
                "role": "user",
                "content": task_description
            })

            # 4. SubAgent主循环（类似nO循环）
            client = model_manager.get_model(self.model_pointer)  # 使用SubAgent独立的模型配置
            openai_tools = self._get_openai_tools()

            iteration = 0
            has_planned = False
            has_used_tavily = False
            while iteration < self.max_iterations:
                iteration += 1
                logger.info(f"📍 SubAgent [{self.name}] Iteration {iteration}/{self.max_iterations}")

                # 4.1 获取上下文并调用模型
                context_messages = self.memory.get_context()
                # 前两轮强制工具调用，促使先规划 TODO 并实际检索；之后允许模型输出总结
                tool_choice = "required" if iteration <= 2 else "auto"
                try:
                    resp = await client.chat(context_messages, tools=openai_tools, tool_choice=tool_choice)
                except TypeError:
                    resp = await client.chat(context_messages)

                content = resp.get("content", "")
                raw_response = resp.get("raw")

                # 4.2 解析tool_calls
                tool_calls = None
                if raw_response and hasattr(raw_response, "choices"):
                    choice = raw_response.choices[0]
                    if hasattr(choice.message, "tool_calls") and choice.message.tool_calls:
                        # 子代理内：仅限制“重型网络工具”的并发，其余（如 TODO 相关）不限制
                        tool_calls_all = choice.message.tool_calls
                        heavy = []
                        light = []
                        for tc in tool_calls_all:
                            n = getattr(tc.function, "name", "")
                            if n.startswith("tavily_") or n.endswith("_subagent"):
                                heavy.append(tc)
                            else:
                                light.append(tc)

                        try:
                            import os as _os
                            max_heavy = int(_os.getenv("SUBAGENT_MAX_HEAVY_CALLS_PER_ITER", "1"))
                        except Exception:
                            max_heavy = 1

                        tool_calls = light + heavy[: max(1, max_heavy) if heavy else 0]

                # 4.3 如果没有工具调用，返回最终结果
                if not tool_calls:
                    if tool_choice == "required":
                        self.memory.add_message({
                            "role": "system",
                            "content": "严格要求：请先调用 create_subagent_todo 规划，再调用 tavily_* 进行检索/抽取。仅输出文字不被接受。"
                        })
                        continue
                    logger.info(f"✅ SubAgent [{self.name}] 任务完成 (iteration={iteration})")

                    if content:
                        self.memory.add_message({"role": "assistant", "content": content})

                    # 🔑 关键优化：生成紧凑的结构化报告
                    return await self._generate_compact_report(content, iteration)

                # 4.4 执行工具调用
                logger.info(f"🔧 SubAgent [{self.name}] 调用 {len(tool_calls)} 个工具")

                # 添加assistant消息
                assistant_msg = {
                    "role": "assistant",
                    "content": content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in tool_calls
                    ],
                }
                self.memory.add_message(assistant_msg)

                # 执行工具
                for tc in tool_calls:
                    tool_name = tc.function.name
                    tool_args = json.loads(tc.function.arguments)

                    # 执行工具
                    exec_result = await self._execute_tool(tool_name, tool_args)

                    result = {
                        "tool_call_id": tc.id,
                        "role": "tool",
                        "name": tool_name,
                        "content": json.dumps(exec_result, ensure_ascii=False)
                    }

                    self.memory.add_message(result)
                    # 记录已规划/已检索信号，配合前两轮强制工具调用一起工作
                    if tool_name == "create_subagent_todo":
                        has_planned = True
                    if tool_name.startswith("tavily_"):
                        has_used_tavily = True

                # 迭代延迟：避免高频调用API导致限流（可选，通过环境变量配置）
                if iteration < self.max_iterations:
                    try:
                        import os as _os
                        import asyncio
                        delay = float(_os.getenv("SUBAGENT_ITERATION_DELAY", "0"))
                        if delay > 0:
                            await asyncio.sleep(delay)
                    except Exception:
                        pass  # 忽略配置错误，继续执行

            # 达到最大迭代次数
            logger.warning(f"⚠️ SubAgent [{self.name}] 达到最大迭代次数({self.max_iterations})")
            return {
                "error": True,
                "message": f"SubAgent [{self.name}] 达到最大迭代次数({self.max_iterations})，任务未完成",
                "data": {
                    "subagent": self.name,
                    "todos": self.todos,
                    "iterations": self.max_iterations
                }
            }

        except Exception as e:
            import traceback
            logger.error(f"❌ SubAgent [{self.name}] 执行异常: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "error": True,
                "message": f"SubAgent [{self.name}] 执行异常: {str(e)}"
            }


# SubAgent工厂函数（类似Claude Code的I2A函数）
async def create_and_execute_subagent(
    subagent_class: type,
    task_description: str,
    context: Optional[Dict[str, Any]] = None,
    session_id: str = "default",  # ✅ 新增：session_id参数
    **kwargs
) -> Dict[str, Any]:
    """创建并执行SubAgent（I2A实例化函数）

    这是SubAgent架构的核心入口点，类似Claude Code的I2A函数

    Args:
        subagent_class: SubAgent类（WindowsSubAgent或BrowserSubAgent）
        task_description: 任务描述
        context: 上下文信息
        session_id: 会话ID，用于TODO隔离
        **kwargs: 传递给SubAgent构造函数的其他参数

    Returns:
        执行结果
    """
    # ✅ 传递session_id给SubAgent
    if 'session_id' not in kwargs:
        kwargs['session_id'] = session_id

    subagent = subagent_class(**kwargs)
    return await subagent.execute(task_description, context)
