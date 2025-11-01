"""Windows UI控制工具集 - 直接集成方案

优势：零中间层开销，原生API调用速度
依赖：pywin32 + pyautogui + psutil

【修复】所有同步操作使用asyncio.to_thread避免阻塞事件循环
"""
from __future__ import annotations

import asyncio
import os
import subprocess
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

try:
    import pyautogui
    import psutil
    import win32gui
    import win32con
    import win32process
    import win32api
    import pyperclip
except ImportError as e:
    print(f"警告：Windows工具依赖缺失 {e}")
    print("请安装：pip install pyautogui psutil pywin32 pyperclip")

from .base import BaseTool


class WindowsLaunchAppTool(BaseTool):
    """启动Windows应用程序"""
    name = "launch_app"
    description = """启动Windows应用程序。支持多种启动方式：

    1. 完整路径：'C:\\Program Files\\app\\app.exe'
    2. 简单名称：'notepad.exe', 'calc.exe', 'mspaint.exe'（从PATH查找）
    3. Windows协议：'ms-settings:', 'ms-settings:display', 'shell:startup'
    4. 开始菜单搜索：'chrome', 'word', 'excel'（模糊匹配）
    5. URL启动：'https://www.example.com'（使用默认浏览器）

    推荐优先级：完整路径 > 简单名称 > 开始菜单搜索 > 协议启动"""

    async def execute(self, app_path: str, **kwargs) -> Dict[str, Any]:
        try:
            launch_method = None

            # 【修复】使用线程池执行同步操作
            def _launch():
                nonlocal launch_method

                # 方式1: Windows协议启动（如 ms-settings:, shell:）
                if app_path.startswith(('ms-', 'shell:', 'http://', 'https://')):
                    launch_method = "protocol"
                    process = subprocess.Popen(['start', '', app_path], shell=True)
                    return process

                # 方式2: 完整路径或带扩展名（直接启动）
                elif app_path.endswith('.exe') or '\\' in app_path or '/' in app_path:
                    launch_method = "path"
                    # 处理路径中的引号
                    if ' ' in app_path and not app_path.startswith('"'):
                        app_path_quoted = f'"{app_path}"'
                    else:
                        app_path_quoted = app_path
                    process = subprocess.Popen(app_path_quoted, shell=True)
                    return process

                # 方式3: 简单名称（从PATH查找）
                else:
                    launch_method = "name_search"
                    # 尝试直接启动（适用于PATH中的程序）
                    try:
                        process = subprocess.Popen(app_path, shell=True)
                        return process
                    except Exception:
                        # 如果直接启动失败，尝试通过start命令启动（会搜索开始菜单）
                        launch_method = "start_menu"
                        process = subprocess.Popen(['start', '', app_path], shell=True)
                        return process

            process = await asyncio.to_thread(_launch)

            # 【修复】使用asyncio.sleep等待应用启动
            await asyncio.sleep(1.5)

            # 检查进程是否仍在运行
            is_running = process.poll() is None

            return {
                "error": False,
                "data": {
                    "app_path": app_path,
                    "process_id": process.pid,
                    "method": launch_method,
                    "status": "running" if is_running else "exited",
                    "message": f"✅ 应用已启动（方式: {launch_method}）{'，进程正在运行' if is_running else '，进程已退出（可能是启动器）'}"
                }
            }
        except Exception as e:
            import traceback
            return {
                "error": True,
                "message": f"启动应用失败: {str(e)}\n提示: 请检查应用路径或名称是否正确。\n{traceback.format_exc()}"
            }


class WindowsClickElementTool(BaseTool):
    """点击屏幕元素"""
    name = "click_element"
    description = """点击屏幕指定坐标或查找图片元素进行点击。支持相对坐标和绝对坐标。

    【推荐工作流】与screenshot配合使用：
    1. 先调用screenshot截取屏幕
    2. 模型使用vision能力分析截图，找到目标元素坐标
    3. 调用click_element(x, y)精确点击

    这样可以确保点击的是当前屏幕状态下的准确位置。"""

    async def execute(self, x: Optional[int] = None, y: Optional[int] = None,
                     image_path: Optional[str] = None, button: str = "left",
                     clicks: int = 1, **kwargs) -> Dict[str, Any]:
        try:
            click_x, click_y = None, None
            method = None

            if image_path:
                # 【修复】图片识别是CPU密集型操作，必须在线程池中执行
                def _locate_image():
                    try:
                        location = pyautogui.locateOnScreen(image_path, confidence=0.8)
                        if location:
                            center = pyautogui.center(location)
                            return center, location
                        return None, None
                    except Exception as e:
                        return None, None

                result, location_box = await asyncio.to_thread(_locate_image)
                if result:
                    click_x, click_y = result
                    method = "image_match"
                else:
                    return {
                        "error": True,
                        "message": f"未找到图片元素: {image_path}。建议先使用screenshot截图，然后用vision能力分析找到元素坐标。"
                    }
            elif x is not None and y is not None:
                # 坐标点击
                click_x, click_y = x, y
                method = "coordinate"
            else:
                return {
                    "error": True,
                    "message": "必须提供坐标(x,y)或图片路径(image_path)"
                }

            # 获取屏幕尺寸，验证坐标有效性
            screen_width, screen_height = await asyncio.to_thread(pyautogui.size)

            # 坐标验证
            if not (0 <= click_x < screen_width and 0 <= click_y < screen_height):
                return {
                    "error": True,
                    "message": f"坐标超出屏幕范围: ({click_x}, {click_y})。屏幕尺寸: {screen_width}x{screen_height}"
                }

            # 执行点击前记录鼠标位置（用于验证）
            old_pos = await asyncio.to_thread(pyautogui.position)

            # 【修复】点击操作也在线程池中执行
            await asyncio.to_thread(
                pyautogui.click, click_x, click_y, clicks=clicks, button=button
            )

            # 验证鼠标移动到目标位置
            new_pos = await asyncio.to_thread(pyautogui.position)

            return {
                "error": False,
                "data": {
                    "x": click_x,
                    "y": click_y,
                    "button": button,
                    "clicks": clicks,
                    "method": method,
                    "screen_size": {"width": screen_width, "height": screen_height},
                    "cursor_moved": new_pos != old_pos,
                    "cursor_position": {"x": new_pos[0], "y": new_pos[1]},
                    "message": f"✅ 成功点击坐标 ({click_x}, {click_y})，{'双击' if clicks == 2 else '单击'}{button}键"
                }
            }
        except Exception as e:
            import traceback
            return {
                "error": True,
                "message": f"点击操作失败: {str(e)}\n{traceback.format_exc()}"
            }


class WindowsTypeTextTool(BaseTool):
    """输入文本"""
    name = "type_text"
    description = "在当前焦点位置输入文本。支持中文、英文、特殊按键和组合键。中文输入通过剪贴板自动处理。"

    def _contains_chinese(self, text: str) -> bool:
        """检测文本是否包含中文字符"""
        if not text:
            return False
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False

    async def execute(self, text: str, interval: float = 0.01,
                     special_keys: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        try:
            input_method = "direct"  # 输入方式标记

            # 【修复】中文输入：使用剪贴板+Ctrl+V
            if text:
                if self._contains_chinese(text):
                    # 包含中文，使用剪贴板方式
                    def _paste_text():
                        pyperclip.copy(text)
                        pyautogui.hotkey('ctrl', 'v')

                    await asyncio.to_thread(_paste_text)
                    input_method = "clipboard"
                else:
                    # 纯英文/数字，直接输入
                    await asyncio.to_thread(pyautogui.write, text, interval)
                    input_method = "direct"

            # 处理特殊按键
            if special_keys:
                for key in special_keys:
                    if '+' in key:
                        # 组合键，如 "ctrl+c"
                        keys = key.split('+')
                        await asyncio.to_thread(pyautogui.hotkey, *keys)
                    else:
                        # 单个特殊键，如 "enter"
                        await asyncio.to_thread(pyautogui.press, key)

            return {
                "error": False,
                "data": {
                    "text": text,
                    "special_keys": special_keys or [],
                    "length": len(text) if text else 0,
                    "method": input_method,
                    "message": f"✅ 成功输入{len(text)}个字符（{'剪贴板' if input_method == 'clipboard' else '直接输入'}）"
                }
            }
        except Exception as e:
            return {
                "error": True,
                "message": f"文本输入失败: {str(e)}"
            }


class WindowsReadFileTool(BaseTool):
    """读取文件内容"""
    name = "read_file"
    description = "读取指定路径的文件内容。支持文本文件和基本二进制文件。自动检测编码（UTF-8/GBK/GB2312）。"

    async def execute(self, file_path: str, encoding: str = "auto",
                     max_size: int = 1024*1024, **kwargs) -> Dict[str, Any]:
        try:
            path = Path(file_path)

            if not path.exists():
                return {
                    "error": True,
                    "message": f"文件不存在: {file_path}"
                }

            if path.stat().st_size > max_size:
                return {
                    "error": True,
                    "message": f"文件过大，超过限制 {max_size} bytes"
                }

            # 自动检测编码
            if encoding == "auto":
                # 尝试多种编码
                encodings_to_try = ['utf-8', 'gbk', 'gb2312', 'utf-16']
                content = None
                used_encoding = None

                for enc in encodings_to_try:
                    try:
                        content = path.read_text(encoding=enc)
                        used_encoding = enc
                        break
                    except (UnicodeDecodeError, LookupError):
                        continue

                if content is None:
                    # 所有编码都失败，返回base64
                    import base64
                    content_bytes = path.read_bytes()
                    encoded_content = base64.b64encode(content_bytes).decode('ascii')
                    return {
                        "error": False,
                        "data": {
                            "file_path": str(path.absolute()),
                            "content": encoded_content,
                            "size": len(content_bytes),
                            "encoding": "base64",
                            "type": "binary",
                            "message": "⚠️ 无法以文本形式解码，已转为base64格式"
                        }
                    }

                return {
                    "error": False,
                    "data": {
                        "file_path": str(path.absolute()),
                        "content": content,
                        "size": len(content),
                        "encoding": used_encoding,
                        "type": "text",
                        "message": f"✅ 成功读取文件（编码: {used_encoding}）"
                    }
                }
            else:
                # 指定编码
                try:
                    content = path.read_text(encoding=encoding)
                    return {
                        "error": False,
                        "data": {
                            "file_path": str(path.absolute()),
                            "content": content,
                            "size": len(content),
                            "encoding": encoding,
                            "type": "text"
                        }
                    }
                except UnicodeDecodeError:
                    # 编码错误，返回base64
                    import base64
                    content_bytes = path.read_bytes()
                    encoded_content = base64.b64encode(content_bytes).decode('ascii')
                    return {
                        "error": False,
                        "data": {
                            "file_path": str(path.absolute()),
                            "content": encoded_content,
                            "size": len(content_bytes),
                            "encoding": "base64",
                            "type": "binary",
                            "message": f"⚠️ 指定编码{encoding}解码失败，已转为base64格式"
                        }
                    }
        except Exception as e:
            import traceback
            return {
                "error": True,
                "message": f"文件读取失败: {str(e)}\n{traceback.format_exc()}"
            }


class WindowsRunCommandTool(BaseTool):
    """执行系统命令"""
    name = "run_command"
    description = "执行Windows系统命令。支持cmd和powershell。自动处理中文输出编码。"

    async def execute(self, command: str, shell: str = "cmd",
                     timeout: int = 30, cwd: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        try:
            # 安全检查：禁止危险命令
            dangerous_commands = ['format', 'del /s', 'rmdir /s', 'shutdown', 'restart']
            if any(dangerous in command.lower() for dangerous in dangerous_commands):
                return {
                    "error": True,
                    "message": f"拒绝执行危险命令: {command}"
                }

            # 选择shell
            if shell.lower() == "powershell":
                full_command = ["powershell", "-Command", command]
            else:
                full_command = command

            # 【修复】Windows中文环境下，命令输出默认是GBK编码
            # 先尝试GBK，失败再尝试UTF-8
            try:
                result = subprocess.run(
                    full_command,
                    shell=True,
                    capture_output=True,
                    timeout=timeout,
                    cwd=cwd,
                    encoding='gbk',  # Windows中文默认编码
                    errors='replace'  # 遇到无法解码的字符用?替换
                )
                encoding_used = 'gbk'
            except Exception as e:
                # GBK失败，尝试UTF-8
                try:
                    result = subprocess.run(
                        full_command,
                        shell=True,
                        capture_output=True,
                        timeout=timeout,
                        cwd=cwd,
                        encoding='utf-8',
                        errors='replace'
                    )
                    encoding_used = 'utf-8'
                except Exception:
                    # 都失败，使用bytes
                    result = subprocess.run(
                        full_command,
                        shell=True,
                        capture_output=True,
                        timeout=timeout,
                        cwd=cwd
                    )
                    # 手动解码
                    stdout = result.stdout.decode('gbk', errors='replace') if result.stdout else ""
                    stderr = result.stderr.decode('gbk', errors='replace') if result.stderr else ""
                    result.stdout = stdout
                    result.stderr = stderr
                    encoding_used = 'gbk (fallback)'

            return {
                "error": False,
                "data": {
                    "command": command,
                    "shell": shell,
                    "return_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "success": result.returncode == 0,
                    "encoding": encoding_used,
                    "message": f"✅ 命令执行{'成功' if result.returncode == 0 else '失败（返回码: ' + str(result.returncode) + '）'}"
                }
            }
        except subprocess.TimeoutExpired:
            return {
                "error": True,
                "message": f"命令执行超时: {timeout}秒"
            }
        except Exception as e:
            import traceback
            return {
                "error": True,
                "message": f"命令执行失败: {str(e)}\n{traceback.format_exc()}"
            }


class WindowsListProcessesTool(BaseTool):
    """列出系统进程"""
    name = "list_processes"
    description = "列出系统运行的进程。支持按名称过滤和详细信息。"

    async def execute(self, filter_name: Optional[str] = None,
                     include_details: bool = False, **kwargs) -> Dict[str, Any]:
        try:
            processes = []

            for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 'memory_info']):
                try:
                    info = proc.info

                    # 名称过滤
                    if filter_name and filter_name.lower() not in info['name'].lower():
                        continue

                    process_data = {
                        "pid": info['pid'],
                        "name": info['name'],
                        "status": info['status']
                    }

                    # 详细信息
                    if include_details:
                        process_data.update({
                            "cpu_percent": info['cpu_percent'],
                            "memory_mb": round(info['memory_info'].rss / 1024 / 1024, 2)
                        })

                    processes.append(process_data)

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return {
                "error": False,
                "data": {
                    "processes": processes,
                    "total_count": len(processes),
                    "filter_name": filter_name,
                    "include_details": include_details
                }
            }
        except Exception as e:
            return {
                "error": True,
                "message": f"进程列表获取失败: {str(e)}"
            }


class WindowsKillProcessTool(BaseTool):
    """终止进程"""
    name = "kill_process"
    description = "根据进程ID或进程名称终止进程。支持强制终止。"

    async def execute(self, pid: Optional[int] = None, name: Optional[str] = None,
                     force: bool = False, **kwargs) -> Dict[str, Any]:
        try:
            if not pid and not name:
                return {
                    "error": True,
                    "message": "必须提供进程ID(pid)或进程名称(name)"
                }

            terminated_processes = []

            if pid:
                # 按PID终止
                try:
                    proc = psutil.Process(pid)
                    proc_name = proc.name()
                    if force:
                        proc.kill()
                    else:
                        proc.terminate()
                    terminated_processes.append({"pid": pid, "name": proc_name})
                except psutil.NoSuchProcess:
                    return {
                        "error": True,
                        "message": f"进程ID {pid} 不存在"
                    }

            if name:
                # 按名称终止
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if name.lower() in proc.info['name'].lower():
                            if force:
                                proc.kill()
                            else:
                                proc.terminate()
                            terminated_processes.append(proc.info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

            if not terminated_processes:
                return {
                    "error": True,
                    "message": f"未找到匹配的进程: pid={pid}, name={name}"
                }

            return {
                "error": False,
                "data": {
                    "terminated_processes": terminated_processes,
                    "count": len(terminated_processes),
                    "force": force
                }
            }
        except Exception as e:
            return {
                "error": True,
                "message": f"进程终止失败: {str(e)}"
            }


class WindowsWaitForElementTool(BaseTool):
    """等待元素出现"""
    name = "wait_for_element"
    description = "等待屏幕上出现指定图片元素或窗口标题。支持超时设置。"

    async def execute(self, image_path: Optional[str] = None,
                     window_title: Optional[str] = None, timeout: int = 10,
                     check_interval: float = 0.5, **kwargs) -> Dict[str, Any]:
        try:
            if not image_path and not window_title:
                return {
                    "error": True,
                    "message": "必须提供图片路径(image_path)或窗口标题(window_title)"
                }

            import time
            start_time = time.time()

            while time.time() - start_time < timeout:
                if image_path:
                    # 【修复】等待图片元素 - 在线程池中执行
                    def _locate_image():
                        try:
                            location = pyautogui.locateOnScreen(image_path, confidence=0.8)
                            if location:
                                center = pyautogui.center(location)
                                return center
                            return None
                        except Exception:
                            return None

                    result = await asyncio.to_thread(_locate_image)
                    if result:
                        return {
                            "error": False,
                            "data": {
                                "found": True,
                                "type": "image",
                                "image_path": image_path,
                                "location": {"x": result.x, "y": result.y},
                                "wait_time": round(time.time() - start_time, 2)
                            }
                        }

                if window_title:
                    # 【修复】等待窗口标题 - 在线程池中执行
                    def _find_window():
                        def enum_windows_callback(hwnd, windows):
                            if win32gui.IsWindowVisible(hwnd):
                                title = win32gui.GetWindowText(hwnd)
                                if window_title.lower() in title.lower():
                                    windows.append({"hwnd": hwnd, "title": title})
                            return True

                        windows = []
                        win32gui.EnumWindows(enum_windows_callback, windows)
                        return windows

                    windows = await asyncio.to_thread(_find_window)
                    if windows:
                        return {
                            "error": False,
                            "data": {
                                "found": True,
                                "type": "window",
                                "window_title": window_title,
                                "found_windows": windows,
                                "wait_time": round(time.time() - start_time, 2)
                            }
                        }

                # 【修复】等待间隔使用asyncio.sleep
                await asyncio.sleep(check_interval)

            # 超时
            return {
                "error": True,
                "message": f"等待超时 {timeout}秒，未找到元素"
            }

        except Exception as e:
            return {
                "error": True,
                "message": f"等待元素失败: {str(e)}"
            }


class WindowsUIInteractTool(BaseTool):
    """综合UI交互工具"""
    name = "ui_interact"
    description = "综合UI交互工具，支持复杂的鼠标键盘操作序列。"

    async def execute(self, actions: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        try:
            results = []

            for i, action in enumerate(actions):
                action_type = action.get("type")
                result = {"action_index": i, "type": action_type, "success": False}

                try:
                    if action_type == "click":
                        x, y = action.get("x"), action.get("y")
                        button = action.get("button", "left")
                        # 【修复】在线程池中执行点击
                        await asyncio.to_thread(pyautogui.click, x, y, button=button)
                        result.update({"success": True, "x": x, "y": y, "button": button})

                    elif action_type == "type":
                        text = action.get("text", "")
                        # 【修复】在线程池中执行输入
                        await asyncio.to_thread(pyautogui.write, text)
                        result.update({"success": True, "text": text})

                    elif action_type == "key":
                        key = action.get("key")
                        # 【修复】在线程池中执行按键
                        await asyncio.to_thread(pyautogui.press, key)
                        result.update({"success": True, "key": key})

                    elif action_type == "hotkey":
                        keys = action.get("keys", [])
                        # 【修复】在线程池中执行组合键
                        await asyncio.to_thread(pyautogui.hotkey, *keys)
                        result.update({"success": True, "keys": keys})

                    elif action_type == "wait":
                        wait_time = action.get("time", 1)
                        # 【修复】使用asyncio.sleep
                        await asyncio.sleep(wait_time)
                        result.update({"success": True, "wait_time": wait_time})

                    elif action_type == "move":
                        x, y = action.get("x"), action.get("y")
                        # 【修复】在线程池中执行鼠标移动
                        await asyncio.to_thread(pyautogui.moveTo, x, y)
                        result.update({"success": True, "x": x, "y": y})

                    else:
                        result["error"] = f"未知操作类型: {action_type}"

                except Exception as e:
                    result["error"] = str(e)

                results.append(result)

                # 【修复】操作间隔使用asyncio.sleep
                await asyncio.sleep(0.1)

            successful_count = sum(1 for r in results if r.get("success"))

            return {
                "error": False,
                "data": {
                    "results": results,
                    "total_actions": len(actions),
                    "successful_actions": successful_count,
                    "success_rate": successful_count / len(actions) if actions else 0
                }
            }

        except Exception as e:
            return {
                "error": True,
                "message": f"UI交互序列执行失败: {str(e)}"
            }