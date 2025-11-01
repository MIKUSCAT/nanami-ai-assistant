"""浏览器坐标操控工具

功能：
- 基于坐标的点击操作（替代playwright）
- 基于坐标的表单填写
- 截图+视觉分析辅助定位

设计理念：
- 使用pyautogui进行鼠标和键盘控制
- 结合screenshot_and_analyze进行视觉定位
- 适用于任何网页浏览器（不依赖特定浏览器API）
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from tools.base import BaseTool


class BrowserClickTool(BaseTool):
    """浏览器坐标点击工具"""

    name = "browser_click"
    description = """在指定坐标位置执行点击操作（适用于浏览器）。

使用场景：
- 点击网页上的按钮、链接、元素
- 配合screenshot_and_analyze定位元素位置

参数说明：
- x, y: 屏幕坐标（绝对坐标）
- click_type: 点击类型（left/right/double）
- duration: 移动到目标位置的耗时（秒）

使用流程：
1. screenshot_and_analyze("找到登录按钮的位置")
2. 获取按钮坐标(x, y)
3. browser_click(x, y)

注意：坐标是屏幕绝对坐标，需要先通过截图分析确定元素位置
"""

    async def execute(
        self,
        x: int,
        y: int,
        click_type: str = "left",
        duration: float = 0.5,
        **kwargs
    ) -> Dict[str, Any]:
        """执行坐标点击

        Args:
            x: X坐标
            y: Y坐标
            click_type: 点击类型（left/right/double）
            duration: 移动耗时（秒）

        Returns:
            执行结果
        """
        try:
            import pyautogui

            # 移动到目标坐标
            pyautogui.moveTo(x, y, duration=duration)

            # 执行点击
            if click_type == "left":
                pyautogui.click()
            elif click_type == "right":
                pyautogui.rightClick()
            elif click_type == "double":
                pyautogui.doubleClick()
            else:
                return {
                    "error": True,
                    "message": f"无效的点击类型: {click_type}（支持：left/right/double）",
                    "data": None
                }

            return {
                "error": False,
                "message": f"✅ 已在坐标({x}, {y})执行{click_type}点击",
                "data": {
                    "x": x,
                    "y": y,
                    "click_type": click_type
                }
            }

        except Exception as e:
            return {
                "error": True,
                "message": f"点击失败: {str(e)}",
                "data": None
            }


class BrowserTypeTool(BaseTool):
    """浏览器文本输入工具"""

    name = "browser_type"
    description = """在浏览器中输入文本（基于坐标定位）。

使用场景：
- 填写表单字段
- 输入搜索关键词
- 输入登录信息

参数说明：
- x, y: 输入框坐标（先点击定位）
- text: 要输入的文本
- interval: 每个字符之间的间隔（秒）
- clear_first: 是否先清空现有内容

使用流程：
1. screenshot_and_analyze("找到搜索框的位置")
2. browser_type(x, y, text="查询内容")

注意：会先点击坐标激活输入框，然后输入文本
"""

    async def execute(
        self,
        x: int,
        y: int,
        text: str,
        interval: float = 0.05,
        clear_first: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """执行文本输入

        Args:
            x: 输入框X坐标
            y: 输入框Y坐标
            text: 要输入的文本
            interval: 字符间隔（秒）
            clear_first: 是否先清空

        Returns:
            执行结果
        """
        try:
            import pyautogui

            # 点击输入框激活
            pyautogui.click(x, y)
            pyautogui.sleep(0.2)  # 等待激活

            # 清空现有内容
            if clear_first:
                pyautogui.hotkey('ctrl', 'a')
                pyautogui.sleep(0.1)
                pyautogui.press('delete')
                pyautogui.sleep(0.1)

            # 输入文本
            pyautogui.write(text, interval=interval)

            return {
                "error": False,
                "message": f"✅ 已在坐标({x}, {y})输入文本: {text[:50]}...",
                "data": {
                    "x": x,
                    "y": y,
                    "text_length": len(text)
                }
            }

        except Exception as e:
            return {
                "error": True,
                "message": f"输入失败: {str(e)}",
                "data": None
            }


class BrowserScrollTool(BaseTool):
    """浏览器滚动工具"""

    name = "browser_scroll"
    description = """滚动浏览器页面。

使用场景：
- 向下滚动查看更多内容
- 向上滚动回到顶部
- 滚动到特定位置

参数说明：
- direction: 滚动方向（up/down）
- amount: 滚动量（像素）
- x, y: 滚动区域坐标（可选，默认鼠标当前位置）
"""

    async def execute(
        self,
        direction: str = "down",
        amount: int = 500,
        x: Optional[int] = None,
        y: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """执行滚动

        Args:
            direction: 方向（up/down）
            amount: 滚动量（像素）
            x, y: 滚动区域坐标

        Returns:
            执行结果
        """
        try:
            import pyautogui

            # 移动到指定坐标（如果提供）
            if x is not None and y is not None:
                pyautogui.moveTo(x, y, duration=0.3)

            # 执行滚动
            scroll_amount = amount if direction == "down" else -amount
            pyautogui.scroll(scroll_amount)

            return {
                "error": False,
                "message": f"✅ 已向{direction}滚动{amount}像素",
                "data": {
                    "direction": direction,
                    "amount": amount
                }
            }

        except Exception as e:
            return {
                "error": True,
                "message": f"滚动失败: {str(e)}",
                "data": None
            }


class BrowserHotkeyTool(BaseTool):
    """浏览器快捷键工具"""

    name = "browser_hotkey"
    description = """执行浏览器快捷键操作。

使用场景：
- 刷新页面（Ctrl+R）
- 打开新标签页（Ctrl+T）
- 前进/后退（Alt+Left/Right）
- 保存页面（Ctrl+S）

参数说明：
- keys: 快捷键组合（如：["ctrl", "r"]）

常用快捷键：
- ["ctrl", "r"]: 刷新
- ["ctrl", "t"]: 新标签页
- ["ctrl", "w"]: 关闭标签页
- ["ctrl", "shift", "t"]: 恢复关闭的标签页
- ["alt", "left"]: 后退
- ["alt", "right"]: 前进
"""

    async def execute(self, keys: list, **kwargs) -> Dict[str, Any]:
        """执行快捷键

        Args:
            keys: 快捷键列表（如["ctrl", "r"]）

        Returns:
            执行结果
        """
        try:
            import pyautogui

            pyautogui.hotkey(*keys)

            return {
                "error": False,
                "message": f"✅ 已执行快捷键: {'+'.join(keys)}",
                "data": {
                    "keys": keys
                }
            }

        except Exception as e:
            return {
                "error": True,
                "message": f"快捷键执行失败: {str(e)}",
                "data": None
            }
