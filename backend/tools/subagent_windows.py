"""
Windows操控SubAgent - 专门处理Windows桌面自动化任务

功能：
- 集成所有Windows工具（应用启动、UI控制、命令执行等）
- 自主规划执行步骤（TODO LIST）
- 隔离的执行环境

使用场景：
- 复杂的Windows自动化流程
- 多步骤UI操作序列
- 需要规划和调整的桌面任务
"""
from __future__ import annotations

from typing import Any, Dict

from core.subagent import SubAgent
from tools.windows_tools import (
    WindowsLaunchAppTool,
    WindowsClickElementTool,
    WindowsTypeTextTool,
    WindowsReadFileTool,
    WindowsRunCommandTool,
    WindowsListProcessesTool,
    WindowsKillProcessTool,
    WindowsWaitForElementTool,
    WindowsUIInteractTool,
)
from tools.vision_screenshot_tools import (
    ScreenshotTool,
    ScreenshotAndAnalyzeTool,
)
from tools.base import BaseTool


class WindowsSubAgent(SubAgent):
    """Windows操控SubAgent

    专门处理Windows桌面自动化任务，具备：
    - 完整的Windows工具集
    - TODO规划能力
    - 自主任务分解和执行
    """

    def __init__(self, max_iterations: int = 15, model_pointer: str = "windows_agent", session_id: str = "default"):
        self.model_pointer = model_pointer  # 使用独立的模型配置
        # 预留：系统提示词（待用户规划）
        system_prompt = """你是Windows操控专家SubAgent，负责执行Windows桌面自动化任务。

**你的角色**: {description}

**可用工具**:
{tool_descriptions}

**执行流程**:
1. 【规划阶段】使用 `create_subagent_todo` 分解任务为具体步骤
2. 【执行阶段】按TODO顺序，使用Windows工具逐步完成
3. 【更新阶段】每完成一步，使用 `update_subagent_todo` 标记状态
4. 【总结阶段】所有任务完成后，总结执行结果

**重要提示**:
- 必须先规划TODO，再执行
- 操作前先检查目标状态（如窗口是否已打开）
- 遇到错误时，调整计划并继续
- 返回清晰的执行报告

**预留：更详细的提示词由用户规划**
"""

        super().__init__(
            name="WindowsSubAgent",
            description="Windows桌面自动化专家，负责应用启动、UI控制、进程管理等任务",
            system_prompt=system_prompt,
            max_iterations=max_iterations,
            model_pointer=model_pointer,  # 使用独立的windows_agent模型
            session_id=session_id  # ✅ 传递session_id
        )

    def _register_tools(self):
        """注册Windows专用工具

        包括：
        - 应用启动工具
        - UI控制工具
        - 文件操作工具
        - 命令执行工具
        - 进程管理工具
        - 截图工具（Vision多模态能力）

        预留：工具注册逻辑，待用户规划具体调用方式
        """
        # 应用启动
        self.tools["launch_app"] = WindowsLaunchAppTool()

        # UI控制
        self.tools["click_element"] = WindowsClickElementTool()
        self.tools["type_text"] = WindowsTypeTextTool()
        self.tools["wait_for_element"] = WindowsWaitForElementTool()
        self.tools["ui_interact"] = WindowsUIInteractTool()

        # 文件操作
        self.tools["read_file"] = WindowsReadFileTool()

        # 命令执行
        self.tools["run_command"] = WindowsRunCommandTool()

        # 进程管理
        self.tools["list_processes"] = WindowsListProcessesTool()
        self.tools["kill_process"] = WindowsKillProcessTool()

        # 截图工具（利用多模态模型进行视觉分析）
        self.tools["screenshot"] = ScreenshotTool()
        self.tools["screenshot_and_analyze"] = ScreenshotAndAnalyzeTool()


class WindowsSubAgentTool(BaseTool):
    """WindowsSubAgent调用工具 - 主Agent使用此工具调用WindowsSubAgent

    这是主Agent和WindowsSubAgent之间的桥梁
    """

    name = "windows_subagent"
    description = """Windows应用操作和进程管理。

✅ 适用场景：
- 启动Windows应用程序
- UI自动化操作
- 进程管理（列举/终止）

SubAgent会自动：
1. 规划UI操作步骤
2. 执行应用启动和控制
3. 管理系统进程
"""

    async def execute(self, task_description: str, context: Dict[str, Any] = None, session_id: str = "default", **kwargs) -> Dict[str, Any]:
        """执行WindowsSubAgent

        Args:
            task_description: 任务描述（详细说明要做什么）
            context: 上下文信息（可选）
            session_id: 会话ID，用于TODO隔离
            **kwargs: 其他参数

        Returns:
            SubAgent执行结果
        """
        from core.subagent import create_and_execute_subagent

        return await create_and_execute_subagent(
            subagent_class=WindowsSubAgent,
            task_description=task_description,
            context=context or {},
            session_id=session_id  # ✅ 传递session_id
        )
