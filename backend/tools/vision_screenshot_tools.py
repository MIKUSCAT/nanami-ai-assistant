"""视觉截图工具 - 利用模型多模态能力替代OCR

功能：
1. ScreenshotTool - 截取屏幕并保存到file_store，返回file_id供模型复用
2. 支持全屏/当前活动窗口截图
3. 截图自动保存，模型可以通过file_id在后续对话中引用

设计理念：
- 不做OCR识别，直接让模型的vision能力处理截图
- 截图保存到file_store（data/uploads/），模型可以通过file_id复用
- 不存储到LTM，避免长期记忆污染
"""
from __future__ import annotations

import asyncio
import os
import base64
import io
from typing import Any, Dict, Optional
from pathlib import Path

try:
    from PIL import ImageGrab, Image
    import pyautogui
    from ctypes import windll
except ImportError as e:
    print(f"警告：截图工具依赖缺失 {e}")
    print("请安装：pip install pillow pyautogui")

from .base import BaseTool
from services.file_store import save_upload


# DPI感知初始化（修复高DPI显示器坐标错位）
try:
    user32 = windll.user32
    user32.SetProcessDPIAware()
    print("✓ 截图工具已启用DPI感知模式")
except Exception as e:
    print(f"⚠ 无法启用DPI感知模式: {e}")


class ScreenshotTool(BaseTool):
    """截图工具 - 截取屏幕并保存到file_store

    核心功能：
    - 截取全屏或当前活动窗口
    - 自动保存到file_store（data/uploads/）
    - 返回file_id，模型可在后续对话中引用
    - 支持多显示器环境

    使用场景：
    1. 用户要求截图查看当前屏幕内容
    2. 记录网页/应用界面供后续分析
    3. 配合playwright等工具，截图验证操作结果

    联合使用示例：
    - 工作流1：playwright_interact打开网页 → screenshot截图 → 模型分析页面内容
    - 工作流2：launch_app启动应用 → screenshot截图 → 模型识别UI元素位置
    - 工作流3：screenshot多次截图 → 模型对比前后变化
    """
    name = "screenshot"
    description = """截取屏幕并保存到file_store，返回file_id供模型查看和复用。

    核心优势：
    - 自动保存：截图保存到data/uploads/，模型可通过file_id在后续对话中引用
    - 多模态识别：模型自动使用vision能力分析截图内容（无需OCR）
    - 灵活截图：支持全屏/当前活动窗口/指定区域截图

    使用场景：
    1. 查看桌面/应用界面："请截图查看当前桌面"
    2. 网页截图："打开网页后截图保存"
    3. 记录操作结果："点击按钮后截图验证"

    重要提示：
    - 截图会保存到file_store，模型可以说"请查看截图file_id: xxx"
    - 不会存储到LTM（长期记忆），不影响未来对话
    - 支持在同一对话中引用多个历史截图
    """

    async def execute(
        self,
        mode: str = "fullscreen",
        all_screens: bool = True,
        window_title: Optional[str] = None,
        region: Optional[Dict[str, int]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """执行截图操作

        Args:
            mode: 截图模式
                - "fullscreen": 全屏截图（默认）
                - "window": 当前活动窗口截图
                - "region": 指定区域截图（需要提供region参数）
            all_screens: 是否截取所有显示器（仅fullscreen模式），默认True
            window_title: 窗口标题（window模式下可选，用于查找特定窗口）
            region: 区域坐标（region模式），格式：{"left": 0, "top": 0, "width": 800, "height": 600}
            **kwargs: 其他参数

        Returns:
            {
                "error": False,
                "data": {
                    "file_id": "xxx",  # 文件ID，可用于后续引用
                    "file_path": "...",  # 文件路径
                    "size": [width, height],  # 图片尺寸
                    "mode": "fullscreen",  # 截图模式
                    "message": "截图已保存，模型可以查看此图片"
                }
            }
        """
        try:
            # 在线程池中执行截图（避免阻塞事件循环）
            def _take_screenshot():
                screenshot = None

                if mode == "fullscreen":
                    # 全屏截图
                    screenshot = ImageGrab.grab(all_screens=all_screens)

                elif mode == "window":
                    # 当前活动窗口截图
                    if window_title:
                        # 查找指定标题的窗口
                        try:
                            import pygetwindow as gw
                            windows = gw.getWindowsWithTitle(window_title)
                            if windows:
                                win = windows[0]
                                win.activate()
                                # 等待窗口激活
                                import time
                                time.sleep(0.2)
                        except Exception as e:
                            print(f"⚠ 查找窗口失败: {e}")

                    # 截取当前活动窗口
                    try:
                        import pygetwindow as gw
                        active_window = gw.getActiveWindow()
                        if active_window:
                            left, top, width, height = active_window.left, active_window.top, active_window.width, active_window.height
                            screenshot = ImageGrab.grab(bbox=(left, top, left + width, top + height))
                        else:
                            # 回退到全屏
                            screenshot = ImageGrab.grab(all_screens=all_screens)
                    except Exception:
                        # pygetwindow不可用，回退到全屏
                        screenshot = ImageGrab.grab(all_screens=all_screens)

                elif mode == "region":
                    # 指定区域截图
                    if not region:
                        return None, "region模式需要提供region参数"

                    left = region.get("left", 0)
                    top = region.get("top", 0)
                    width = region.get("width", 800)
                    height = region.get("height", 600)

                    bbox = (left, top, left + width, top + height)
                    screenshot = ImageGrab.grab(bbox=bbox)

                else:
                    return None, f"不支持的截图模式: {mode}"

                if not screenshot:
                    return None, "截图失败"

                return screenshot, None

            screenshot, error = await asyncio.to_thread(_take_screenshot)

            if error:
                return {
                    "error": True,
                    "message": error
                }

            # 保存截图到file_store
            # 【优化】图片压缩：根据尺寸选择压缩策略
            img_byte_arr = io.BytesIO()

            # 获取图片尺寸
            width, height = screenshot.size
            total_pixels = width * height

            # 压缩策略：
            # - 小图(<1M像素): PNG无损压缩
            # - 中图(1-4M像素): PNG优化压缩
            # - 大图(>4M像素): JPEG 85质量压缩
            if total_pixels < 1000000:  # <1M像素
                screenshot.save(img_byte_arr, format='PNG', optimize=True)
                format_used = "PNG"
            elif total_pixels < 4000000:  # 1-4M像素
                screenshot.save(img_byte_arr, format='PNG', optimize=True, compress_level=9)
                format_used = "PNG (optimized)"
            else:  # >4M像素
                # 转换为RGB（JPEG不支持透明通道）
                if screenshot.mode in ('RGBA', 'LA', 'P'):
                    rgb_screenshot = Image.new('RGB', screenshot.size, (255, 255, 255))
                    rgb_screenshot.paste(screenshot, mask=screenshot.split()[-1] if screenshot.mode == 'RGBA' else None)
                    screenshot = rgb_screenshot
                screenshot.save(img_byte_arr, format='JPEG', quality=85, optimize=True)
                format_used = "JPEG (compressed)"

            img_bytes = img_byte_arr.getvalue()
            original_size = len(img_bytes)

            # 生成文件名
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # 根据格式选择扩展名
            ext = ".jpg" if "JPEG" in format_used else ".png"
            filename = f"screenshot_{mode}_{timestamp}{ext}"

            # 保存到file_store
            file_id = save_upload(filename, img_bytes)

            # 获取保存路径
            from services.file_store import get_file_path_by_id, get_image_as_base64
            file_path = get_file_path_by_id(file_id)

            # 获取图片的base64数据（用于模型查看）
            image_base64_data = get_image_as_base64(file_id)

            # 计算压缩率
            compression_ratio = round((1 - original_size / (width * height * 4)) * 100, 1) if width * height > 0 else 0

            result = {
                "error": False,
                "data": {
                    "file_id": file_id,
                    "file_path": file_path,
                    "size": list(screenshot.size),
                    "file_size": original_size,
                    "file_size_mb": round(original_size / 1024 / 1024, 2),
                    "format": format_used,
                    "compression_ratio": f"{compression_ratio}%",
                    "mode": mode,
                    "all_screens": all_screens if mode == "fullscreen" else None,
                    "window_title": window_title if mode == "window" else None,
                    "region": region if mode == "region" else None,
                    "message": f"✅ 截图已保存（file_id: {file_id}，尺寸: {screenshot.size[0]}x{screenshot.size[1]}，{round(original_size/1024, 1)}KB，格式: {format_used}）。\n\n📸 截图预览已包含在工具结果中，你可以直接查看。\n\n💾 如需保存到本地，请使用 save_cached_file 工具。"
                }
            }

            # 如果成功获取base64，添加到结果中（供模型查看）
            if image_base64_data:
                result["data"]["image_preview"] = {
                    "url": image_base64_data["url"],
                    "mime_type": image_base64_data["mime_type"]
                }

            return result

        except Exception as e:
            import traceback
            return {
                "error": True,
                "message": f"截图失败: {str(e)}\n{traceback.format_exc()}"
            }


class ScreenshotAndAnalyzeTool(BaseTool):
    """截图并立即分析工具（快捷方式）

    功能：
    - 截图 + 提供提示词，让模型立即分析截图内容
    - 一步完成截图和分析，无需手动引用file_id
    - 适用于快速查看屏幕内容的场景
    """
    name = "screenshot_and_analyze"
    description = """截取屏幕并立即让模型分析内容。一步完成截图+分析。

    使用场景：
    1. "截图并告诉我屏幕上显示了什么"
    2. "截图并找到登录按钮的位置"
    3. "截图并识别页面中的错误信息"

    与screenshot工具的区别：
    - screenshot: 仅截图保存，模型需要手动查看file_id
    - screenshot_and_analyze: 截图后立即分析，返回分析结果
    """

    async def execute(
        self,
        prompt: str = "请描述这张截图中显示的内容",
        mode: str = "fullscreen",
        all_screens: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """执行截图并分析

        Args:
            prompt: 分析提示词，默认"请描述这张截图中显示的内容"
            mode: 截图模式（fullscreen/window/region）
            all_screens: 是否截取所有显示器
            **kwargs: 其他参数

        Returns:
            {
                "error": False,
                "data": {
                    "file_id": "xxx",
                    "analysis": "模型分析结果",
                    "size": [width, height]
                }
            }
        """
        try:
            # 1. 截图
            screenshot_tool = ScreenshotTool()
            screenshot_result = await screenshot_tool.execute(mode=mode, all_screens=all_screens, **kwargs)

            if screenshot_result.get("error"):
                return screenshot_result

            file_id = screenshot_result["data"]["file_id"]

            # 2. 加载截图为base64
            from services.file_store import get_image_as_base64
            image_data = get_image_as_base64(file_id)

            if not image_data:
                return {
                    "error": True,
                    "message": "截图保存成功但无法加载图片数据"
                }

            # 3. 调用模型分析
            from core.model_manager import model_manager
            client = model_manager.get_model("main")

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_data["url"]
                            }
                        }
                    ]
                }
            ]

            response = await client.chat(messages, temperature=0.1)
            analysis = response.get("content", "")

            return {
                "error": False,
                "data": {
                    "file_id": file_id,
                    "file_path": screenshot_result["data"]["file_path"],
                    "size": screenshot_result["data"]["size"],
                    "prompt": prompt,
                    "analysis": analysis,
                    "message": f"截图已完成并分析（file_id: {file_id}）"
                }
            }

        except Exception as e:
            import traceback
            return {
                "error": True,
                "message": f"截图分析失败: {str(e)}\n{traceback.format_exc()}"
            }
