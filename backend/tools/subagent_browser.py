"""
浏览器操控SubAgent（复杂场景友好版：视觉坐标 + Playwright有头）

目标：
- 在保持你现有“截图→视觉→坐标操作→验证”的极简闭环基础上，新增 Playwright 有头工具，
  为【复杂/多步骤/动态页面】提供“选择器优先”的稳健路径；两条链路可并存与互补。
- 严格遵循 README 的 SubAgent 结构与紧凑报告约束；支持 TODO LIST 的复杂任务规划。

关键点：
- 所有浏览器操作均为“有头（headed）”；Playwright 启动时强制 headless=False。
- 简单任务：优先走视觉 + 坐标快通道（少步骤、直达）。
- 复杂任务（≥3步、多页面跳转、动态加载、表单校验）：开启 TODO，优先用 Playwright 选择器
  （get_by_role/get_by_text/locator），动作前后必做验证。
- 依然支持“截图 + 视觉分析”作为 Playwright 的验证/兜底手段。

参考与对齐：
- README 的 SubAgent 分层、TODO、紧凑报告、视觉循环与“工具内聚”。             # noqa
- 你之前的 subagent_browser.py 坐标链路工具：click/type/scroll/hotkey。         # noqa
- Playwright 官方：headless=False（有头）、Locator/get_by_role/get_by_text、    # noqa
  自动等待（auto-wait）与 actionability。                                       # noqa
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.subagent import SubAgent
from tools.browser_coordinate_tools import (
    BrowserClickTool,
    BrowserTypeTool,
    BrowserScrollTool,
    BrowserHotkeyTool,
)
from tools.vision_screenshot_tools import (
    ScreenshotTool,
    ScreenshotAndAnalyzeTool,
)
from tools.base import BaseTool

# ========================
# 内置 Playwright 有头控制
# ========================

# 说明：
# - 作为“选择器优先”的稳健路径，适配复杂页面/多步骤流程；
# - 首次调用自动启动有头浏览器（chromium，headless=False），保持单会话单页；
# - 支持 goto / click / fill / type / press / wait_for / wait_load / hover / scroll / close；
# - 选择器策略：优先 role/name → 其次 text → 再次 css/xpath；返回 url/title 作为轻反馈。
#
# 参考：
# - Playwright Python Library: “set headless=False to see the browser UI”。
# - Locator / get_by_role / get_by_text。
# - Auto-wait & actionability（Playwright 会在交互前做可操作性检查并自动等待）。
#
# 官方文档：
#   https://playwright.dev/python/docs/library
#   https://playwright.dev/python/docs/locators
#   https://playwright.dev/docs/actionability


_PW_SINGLETON: Dict[str, Any] = {
    "playwright": None,
    "browser": None,
    "context": None,
    "page": None,
}


class PlaywrightInteractTool(BaseTool):
    """
    名称: playwright_interact
    功能: 有头浏览器的稳健交互（选择器优先）。支持：
          launch/goto/click/fill/type/press/wait_for/wait_load/hover/scroll/close
    典型用法（由 LLM 选择，复杂任务优先）:
      - playwright_interact(action="goto", url="https://example.com")
      - playwright_interact(action="click", role="button", name="登录")
      - playwright_interact(action="fill", label="用户名", text="user@example.com")
      - playwright_interact(action="press", key="Enter")
      - playwright_interact(action="wait_for", role="heading", name="仪表盘")
      - playwright_interact(action="wait_load", state="networkidle")
    """

    name = "playwright_interact"
    description = "Playwright 有头浏览器控制（选择器优先；复杂任务推荐）。"

    async def _ensure_launched(self):
        if _PW_SINGLETON["browser"] and _PW_SINGLETON["page"]:
            return

        # 延迟导入，避免未使用时报错
        from playwright.async_api import async_playwright

        _PW_SINGLETON["playwright"] = await async_playwright().start()
        # 强制有头（headed）
        _PW_SINGLETON["browser"] = await _PW_SINGLETON["playwright"].chromium.launch(
            headless=False  # 官方说明：默认 headless，设 False 即 headed
        )
        _PW_SINGLETON["context"] = await _PW_SINGLETON["browser"].new_context()
        _PW_SINGLETON["page"] = await _PW_SINGLETON["context"].new_page()

    def _resolve_locator(self, page, **kw):
        """
        选择器解析优先级：
          1) role + name（语义稳健，推荐）
          2) text（get_by_text）
          3) label（输入框/复选）
          4) selector（css/xpath 等）
        """
        role = kw.get("role")
        name = kw.get("name")
        text = kw.get("text")
        label = kw.get("label")
        selector = kw.get("selector")

        if role:
            # page.get_by_role("button", name="登录")
            return page.get_by_role(role=role, name=name) if name else page.get_by_role(role=role)
        if text:
            return page.get_by_text(text=text, exact=kw.get("exact", False))
        if label:
            return page.get_by_label(text=label, exact=kw.get("exact", False))
        if selector:
            return page.locator(selector)

        raise ValueError("需要提供 role/name 或 text/label 或 selector 之一以定位元素。")

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Args:
          action: "launch" | "goto" | "click" | "fill" | "type" | "press"
                  | "wait_for" | "wait_load" | "hover" | "scroll" | "close"
        Returns:
          dict(status, url, title, note)
        """
        from playwright.async_api import TimeoutError as PWTimeoutError

        try:
            if action == "launch":
                await self._ensure_launched()
                page = _PW_SINGLETON["page"]
                return {"status": "ok", "url": page.url, "title": await page.title(), "note": "launched"}

            # 默认任何动作前都确保已启动
            await self._ensure_launched()
            page = _PW_SINGLETON["page"]

            if action == "goto":
                url = kwargs.get("url")
                assert url, "goto 需要提供 url"
                await page.goto(url)
                return {"status": "ok", "url": page.url, "title": await page.title()}

            if action == "click":
                loc = self._resolve_locator(page, **kwargs)
                await loc.click()  # Playwright 自动等待与 actionability 检查
                return {"status": "ok", "url": page.url, "title": await page.title()}

            if action == "fill":
                loc = self._resolve_locator(page, **kwargs)
                text = kwargs.get("text", "")
                await loc.fill(text)
                return {"status": "ok", "url": page.url, "title": await page.title()}

            if action == "type":
                # 常用于已聚焦或先 click 再 type
                text = kwargs.get("text", "")
                await page.keyboard.type(text)
                if kwargs.get("press_enter"):
                    await page.keyboard.press("Enter")
                return {"status": "ok", "url": page.url, "title": await page.title()}

            if action == "press":
                key = kwargs.get("key", "")
                assert key, "press 需要 key"
                await page.keyboard.press(key)
                return {"status": "ok", "url": page.url, "title": await page.title()}

            if action == "wait_for":
                # 等待某个元素就绪（role/text/label/selector）
                loc = self._resolve_locator(page, **kwargs)
                timeout = kwargs.get("timeout", 10000)
                await loc.wait_for(state=kwargs.get("state", "visible"), timeout=timeout)
                return {"status": "ok", "url": page.url, "title": await page.title(), "note": "wait_for passed"}

            if action == "wait_load":
                state = kwargs.get("state", "load")  # "load" | "domcontentloaded" | "networkidle"
                timeout = kwargs.get("timeout", 15000)
                await page.wait_for_load_state(state=state, timeout=timeout)
                return {"status": "ok", "url": page.url, "title": await page.title(), "note": f"loadstate={state}"}

            if action == "hover":
                loc = self._resolve_locator(page, **kwargs)
                await loc.hover()
                return {"status": "ok", "url": page.url, "title": await page.title()}

            if action == "scroll":
                # 滚动窗口（相对滚动）
                delta_y = kwargs.get("delta_y", 600)
                await page.mouse.wheel(0, delta_y)
                return {"status": "ok", "url": page.url, "title": await page.title()}

            if action == "close":
                if _PW_SINGLETON["context"]:
                    await _PW_SINGLETON["context"].close()
                if _PW_SINGLETON["browser"]:
                    await _PW_SINGLETON["browser"].close()
                if _PW_SINGLETON["playwright"]:
                    await _PW_SINGLETON["playwright"].stop()
                for k in _PW_SINGLETON.keys():
                    _PW_SINGLETON[k] = None
                return {"status": "ok", "note": "closed"}

            return {"status": "error", "note": f"unknown action: {action}"}

        except PWTimeoutError as e:
            return {"status": "timeout", "note": str(e)}
        except Exception as e:
            return {"status": "error", "note": str(e)}


# =======================
# SubAgent（注册两套工具）
# =======================

class BrowserSubAgent(SubAgent):
    """
    浏览器操控SubAgent（复杂场景友好）

    - 视觉坐标链路：Screenshot/ScreenshotAndAnalyze → BrowserClick/Type/Scroll/Hotkey
    - Playwright有头链路：playwright_interact（选择器优先，适合复杂/动态流程）
    - TODO 规划：复杂任务优先创建 TODO（≤8 步，每步可有微循环 Observe→Act→Verify）
    """

    def __init__(
        self,
        max_iterations: int = 15,
        model_pointer: str = "browser_agent",
        session_id: str = "default",
    ):
        self.model_pointer = model_pointer

        system_prompt = f"""你是“浏览器操控 SubAgent（复杂场景友好版）”。你的目标是在**尽量少的迭代**
完成任务，并在【复杂场景】充分利用 TODO 规划与 Playwright 有头选择器的稳健性。

==================== 工具概览 ====================
{{tool_descriptions}}

两条互补链路（由你按情境自选）：
A) 视觉坐标快通道（简单任务）：
   - screenshot / screenshot_and_analyze 产生 bbox
   - browser_click / browser_type / browser_scroll / browser_hotkey
B) 选择器优先（复杂任务推荐）：
   - playwright_interact：launch/goto/click/fill/type/press/wait_for/wait_load/hover/scroll/close
   - 使用 get_by_role/name 或 get_by_text/label 或 css/xpath 定位；交互后用 screenshot_and_analyze 验证

==================== 何时启用 TODO ====================
- 满足任一条件请**创建 TODO**：需要登录/多页面跳转/表单校验/筛选检索/多结果比对/≥3 步。
- TODO 条目 ≤ 8；每个 TODO 在执行时遵循“微循环”：
  O-Observe   ：screenshot_and_analyze 或 playwright_interact(wait_for/wait_load)
  A-Act       ：browser_* 或 playwright_interact(click/fill/type/press/scroll)
  V-Verify    ：screenshot_and_analyze 或 playwright_interact(wait_for) 进行术后验证
- 简单目标（1~2 步）可跳过 TODO，直接执行并验证。

==================== 选择策略 ====================
- 能清晰写出语义目标（如“点击‘登录’按钮/出现‘仪表盘’标题”）→ 优先 Playwright 选择器（更稳），
  失败再退回视觉坐标。
- 目标是明显的可见元素（位置已知/截图易识别）→ 直接视觉坐标更快。
- 输入前必须聚焦：若使用坐标则先 click 再 type；使用 Playwright 可 fill 或先 click 后 type。
- 任何一步失败最多重试 2 次；必要时小幅 scroll 后重试。

==================== 验证与报告 ====================
- 关键步骤后务必验证（出现目标文本/标题/URL片段等）。
- 最终生成紧凑报告（summary/关键发现/artifacts 文件ID/todo 完成度）。
- 保持描述简洁，不回放长过程。

（注意：Playwright 已固定有头模式；仅在需要时主动调用 playwright_interact("launch")，否则首次动作会自动拉起。）"""

        super().__init__(
            name="BrowserSubAgent",
            description="浏览器自动化专家（视觉坐标 + Playwright有头；支持 TODO 规划）",
            system_prompt=system_prompt,
            max_iterations=max_iterations,
            model_pointer=model_pointer,
            session_id=session_id,
        )

    def _register_tools(self):
        # 视觉链路（保留）
        self.tools["screenshot"] = ScreenshotTool()
        self.tools["screenshot_and_analyze"] = ScreenshotAndAnalyzeTool()

        self.tools["browser_click"] = BrowserClickTool()
        self.tools["browser_type"] = BrowserTypeTool()
        self.tools["browser_scroll"] = BrowserScrollTool()
        self.tools["browser_hotkey"] = BrowserHotkeyTool()

        # Playwright 有头链路（新增）
        self.tools["playwright_interact"] = PlaywrightInteractTool()


class BrowserSubAgentTool(BaseTool):
    """BrowserSubAgent 调用工具（主 Agent 侧用）"""

    name = "browser_subagent"
    description = """网页交互自动化（视觉坐标 + Playwright有头；复杂任务支持 TODO 与选择器优先）。"""

    async def execute(
        self,
        task_description: str,
        context: Dict[str, Any] = None,
        session_id: str = "default",
        **kwargs,
    ) -> Dict[str, Any]:
        """执行 BrowserSubAgent"""
        from core.subagent import create_and_execute_subagent

        return await create_and_execute_subagent(
            subagent_class=BrowserSubAgent,
            task_description=task_description,
            context=context or {},
            session_id=session_id,
        )
