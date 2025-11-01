"""
Agent 核心循环（含记忆、压缩、工具调用、长期记忆提炼）

特性：
- 参�?Claude Code 的思路：工具调用闭环、上下文压缩
- 在会话结�?达到迭代上限时，触发一次“用户偏好”提炼并写入 Markdown（可通过环境变量开关）
"""
from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Dict, List, Optional

from core.model_manager import model_manager
from core.memory import MemoryManager
from core.prompts import get_system_message
from core.ltm import LTMMarkdown, ltm_md_enabled
from services.file_store import (
    get_file_content_by_id,
    get_file_path_by_id,
    get_image_as_base64,
    is_image_file
)
from tools.manager import tool_manager


def _truncate_large_tool_result(tool_result: Dict[str, Any]) -> Dict[str, Any]:
    """截断大型工具结果，避免上下文爆炸

    策略：
    1. 检测 base64 编码的数据（截图、PDF等）
    2. 缓存到file_store，获取file_id
    3. 返回file_id + 元数据（LLM可以后续使用）
    4. 保留摘要信息

    Args:
        tool_result: 原始工具结果，格式：{"role": "tool", "content": "...", "name": "..."}

    Returns:
        截断后的工具结果
    """
    import os
    from services.file_store import cache_base64_data

    # 获取截断阈值（环境变量配置，默认10KB）
    try:
        max_size = int(os.getenv("TOOL_RESULT_MAX_SIZE", "10240"))  # 10KB
    except Exception:
        max_size = 10240

    content_str = tool_result.get("content", "")

    # 如果内容不大，直接返回
    if len(content_str) <= max_size:
        return tool_result

    # 尝试解析JSON
    try:
        content_data = json.loads(content_str)
    except json.JSONDecodeError:
        # 不是JSON，直接截断文本
        truncated_content = content_str[:max_size] + f"\n\n[... 内容过长，已截断 {len(content_str)} 字符中的 {len(content_str) - max_size} 字符]"
        return {
            **tool_result,
            "content": truncated_content
        }

    # 检查是否包含大型 base64 数据
    if isinstance(content_data, dict) and "data" in content_data:
        data = content_data["data"]
        truncated = False

        # 处理 base64 编码的图片
        if isinstance(data, dict) and "screenshot" in data and isinstance(data["screenshot"], str):
            original_size = len(data["screenshot"])
            if original_size > 1000:  # 大于1000字符
                # 【关键修复】缓存base64数据
                file_id = cache_base64_data(
                    data["screenshot"],
                    file_type="screenshot",
                    metadata={
                        "format": data.get("format", "png"),
                        "url": data.get("url"),
                        "original_size": original_size
                    }
                )

                # 替换base64为file_id引用
                data["screenshot"] = data["screenshot"][:100] + "...[已缓存]"
                data["screenshot_size"] = f"{original_size} 字符 (~{original_size // 1024}KB)"
                data["screenshot_file_id"] = file_id  # ✅ LLM可以使用这个ID
                data["screenshot_truncated"] = True
                data["_summary"] = f"✅ 截图已成功生成并缓存（file_id: {file_id}）。使用 save_cached_file 工具可将其保存到本地。"
                truncated = True

        # 处理 base64 编码的 PDF
        if isinstance(data, dict) and "pdf" in data and isinstance(data["pdf"], str):
            original_size = len(data["pdf"])
            if original_size > 1000:
                # 【关键修复】缓存base64数据
                file_id = cache_base64_data(
                    data["pdf"],
                    file_type="pdf",
                    metadata={
                        "format": data.get("format", "A4"),
                        "url": data.get("url"),
                        "original_size": original_size
                    }
                )

                # 替换base64为file_id引用
                data["pdf"] = data["pdf"][:100] + "...[已缓存]"
                data["pdf_size"] = f"{original_size} 字符 (~{original_size // 1024}KB)"
                data["pdf_file_id"] = file_id  # ✅ LLM可以使用这个ID
                data["pdf_truncated"] = True
                data["_summary"] = f"✅ PDF已成功生成并缓存（file_id: {file_id}）。使用 save_cached_file 工具可将其保存到本地。"
                truncated = True

        # 处理长文本内容
        if isinstance(data, dict) and "text" in data and isinstance(data["text"], str):
            original_size = len(data["text"])
            if original_size > max_size:
                data["text"] = data["text"][:max_size] + f"\n\n...[文本过长，已截断 {original_size - max_size} 字符]"
                data["text_size"] = f"{original_size} 字符"
                data["text_truncated"] = True
                truncated = True

        if truncated:
            # 重新序列化
            return {
                **tool_result,
                "content": json.dumps(content_data, ensure_ascii=False)
            }

    # 如果没有特殊处理，但内容仍然很大，直接截断JSON
    if len(content_str) > max_size:
        return {
            **tool_result,
            "content": content_str[:max_size] + f"\n\n[... JSON过大，已截断]"
        }

    return tool_result


async def _process_subagent_report(
    tool_result: Dict[str, Any],
    next_round_images: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """处理SubAgent报告（核心优化）

    Args:
        tool_result: SubAgent工具返回结果
        next_round_images: 图片列表（会被修改，添加artifacts中的图片）

    Returns:
        {
            "memory_message": {...},  # 注入到主Agent记忆的紧凑消息
            "user_message": "..."      # 展示给用户的格式化消息
        }
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        # 解析SubAgent报告
        content_str = tool_result.get("content", "{}")
        report = json.loads(content_str)

        # 提取报告字段
        if isinstance(report, dict) and not report.get("error", False):
            summary = report.get("summary", "SubAgent执行完成")
            key_findings = report.get("key_findings", [])
            artifacts = report.get("artifacts", [])
            todos_completed = report.get("todos_completed", 0)
            todos_total = report.get("todos_total", 0)
            iterations = report.get("iterations", 0)
            subagent_name = report.get("subagent", "SubAgent")

            # 处理artifacts：如果是图片，注入到next_round_images
            for artifact_id in artifacts:
                file_path = get_file_path_by_id(artifact_id)
                if file_path and is_image_file(file_path):
                    image_data = get_image_as_base64(artifact_id)
                    if image_data:
                        next_round_images.append({
                            "type": "image_url",
                            "image_url": {
                                "url": image_data["url"]
                            }
                        })
                        logger.info(f"📸 SubAgent返回截图 file_id: {artifact_id}，将在下一轮注入")

            # 生成用户友好的格式化消息
            user_message = f"""
✅ **{subagent_name}执行报告**

**摘要**：{summary}

**关键发现**：
{chr(10).join(f"- {finding}" for finding in key_findings[:10]) if key_findings else "（无）"}

**附件**：{len(artifacts)}个文件（file_id: {", ".join(artifacts[:5])}{"..." if len(artifacts) > 5 else ""}）

**执行情况**：完成 {todos_completed}/{todos_total} 个任务，迭代 {iterations} 轮
"""

            # 生成注入到memory的紧凑消息
            memory_message = {
                "tool_call_id": tool_result.get("tool_call_id"),
                "role": "tool",
                "name": tool_result.get("name"),
                "content": json.dumps({
                    "error": False,
                    "data": {
                        "subagent": subagent_name,
                        "summary": summary,
                        "key_findings": key_findings[:5],  # 只保留前5条
                        "artifacts_count": len(artifacts),
                        "todos_status": f"{todos_completed}/{todos_total}",
                        "iterations": iterations
                    }
                }, ensure_ascii=False)
            }

            return {
                "memory_message": memory_message,
                "user_message": user_message
            }

        else:
            # SubAgent执行失败
            error_message = report.get("message", "SubAgent执行失败")
            user_message = f"❌ SubAgent执行失败：{error_message}"

            memory_message = {
                "tool_call_id": tool_result.get("tool_call_id"),
                "role": "tool",
                "name": tool_result.get("name"),
                "content": json.dumps({
                    "error": True,
                    "message": error_message
                }, ensure_ascii=False)
            }

            return {
                "memory_message": memory_message,
                "user_message": user_message
            }

    except Exception as e:
        logger.error(f"处理SubAgent报告异常: {e}")
        # 降级处理：返回原始内容
        return {
            "memory_message": tool_result,
            "user_message": tool_result.get("content", "SubAgent报告解析失败")
        }


async def agent_main_loop(
    user_input: str,
    file_ids: Optional[List[str]] = None,
    max_iterations: int = 999,
    save_ltm: bool = False,
    history_messages: Optional[List[Dict[str, Any]]] = None,
    session_id: Optional[str] = None,  # 会话ID（前端对话窗口ID）
) -> AsyncGenerator[Dict[str, Any], None]:
    """Agent 主循环：支持记忆、压缩、工具调用与长期记忆提炼

    核心修改：接收前端传递的 session_id，实现对话窗口级别的上下文持久化

    Args:
        user_input: 当前用户输入
        file_ids: 附件ID列表
        max_iterations: 最大迭代次数
        save_ltm: 是否保存长期记忆
        history_messages: 历史消息列表（前端传递），格式：[{"role": "user|assistant", "content": "..."}]
        session_id: 会话ID（前端对话窗口ID，用于TODO和对话持久化隔离）

    Yields:
        事件流：{"type": "meta|content|tool_call|tool_result|done", "data": ...}
    """
    # 初始化日志
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # 核心修改：使用前端传递的 session_id 创建 MemoryManager
    # 如果前端未传递，则自动生成新 UUID（保持向后兼容）
    memory = MemoryManager(session_id=session_id)

    # 日志记录会话ID，便于调试和追踪
    logger.info(f"🎯 Agent主循环启动: session_id={memory.session_id}")

    # 1) 注入系统提示（含七海人格 + 工具说明）
    tool_descriptions = tool_manager.get_tool_descriptions()
    system_msg = get_system_message(tool_descriptions)
    memory.add_message(system_msg)

    # 2) 加载长期记忆（LTM）到上下文
    if ltm_md_enabled():
        try:
            ltm = LTMMarkdown()
            ltm_content = ltm.read_all()
            if ltm_content and ltm_content.strip():
                memory.add_message({
                    "role": "system",
                    "content": f"## 哥哥的长期偏好（从历史对话中提炼）\n\n{ltm_content}"
                })
                logger.info(f"✅ 已加载完整长期记忆到上下文")
        except Exception as e:
            logger.warning(f"⚠️ 加载长期记忆失败: {e}")

    # 3) 注入历史消息（如果前端传递了历史）
    if history_messages:
        # 只加载用户和助手的历史消息，跳过系统消息（系统消息已经在步骤1注入）
        for msg in history_messages:
            if msg.get("role") in ["user", "assistant"]:
                memory.add_message(msg)

    # 4) 注入附件内容
    # - 图片文件：转换为base64并使用vision格式
    # - 文本文件：作为system消息注入
    image_contents = []  # 存储图片的base64数据

    if file_ids:
        for fid in file_ids:
            file_path = get_file_path_by_id(fid)

            # 检查是否是图片文件
            if file_path and is_image_file(file_path):
                # 获取图片的base64编码
                image_data = get_image_as_base64(fid)
                if image_data:
                    image_contents.append({
                        "type": "image_url",
                        "image_url": {
                            "url": image_data["url"]
                        }
                    })
                    logger.info(f"✅ 已加载图片文件: {fid} ({image_data['mime_type']})")
            else:
                # 文本文件，直接读取内容
                content = get_file_content_by_id(fid)
                if content:
                    snippet = content[:20000]
                    memory.add_message({
                        "role": "system",
                        "content": f"[附件:{fid}]\n{snippet}",
                    })
                    logger.info(f"✅ 已加载文本文件: {fid}")

    # 5) 添加当前用户输入
    # 如果有图片，使用多模态消息格式（OpenAI Vision格式）
    if image_contents:
        # 构造多模态消息：[{"type": "text", "text": "..."}, {"type": "image_url", "image_url": {...}}]
        user_message_content = [
            {"type": "text", "text": user_input}
        ]
        user_message_content.extend(image_contents)

        memory.add_message({
            "role": "user",
            "content": user_message_content
        })
        logger.info(f"✅ 已添加多模态用户消息（文本 + {len(image_contents)}张图片）")
    else:
        # 纯文本消息
        memory.add_message({"role": "user", "content": user_input})

    # 6) 上下文压缩检查
    compact_state = await memory.check_and_compact()
    yield {"type": "meta", "data": {"compact": compact_state}}

    # 7) 加载已存在的TODO（跨会话恢复）- 只加载当前session的TODO
    from services.todo_store import list_todos
    existing_todos = list_todos(session_id=memory.session_id)  # 🔑 关键：传入session_id隔离TODO

    if existing_todos:
        pending_todos = [t for t in existing_todos if t.status in ["pending", "in_progress"]]

        if pending_todos:
            logger.info(f"✅ 检测到 {len(pending_todos)} 个未完成的TODO，准备继续执行")

            # 注入System Reminder，提示模型继续执行
            todo_summary = "\n".join([
                f"- [{t.status}] {t.title}: {t.description or '无描述'}"
                for t in pending_todos[:10]  # 最多显示10个
            ])

            memory.add_message({
                "role": "system",
                "content": f"""<system-reminder>
📋 **检测到未完成的TODO任务**

你之前创建了以下任务清单，现在可以继续执行：

{todo_summary}

请继续完成这些未完成的任务。你可以：
1. 使用 update_todo 更新任务状态为 in_progress 或 completed
2. 直接调用相关工具继续执行
3. 如果任务已完成，标记为 completed

不需要重新创建TODO LIST，直接继续执行即可。
</system-reminder>"""
            })

            yield {
                "type": "meta",
                "data": {
                    "todos_loaded": True,
                    "pending_count": len(pending_todos),
                    "total_count": len(existing_todos)
                }
            }

    # 8) 主循环（思考→工具→再思考）
    main_client = model_manager.get_model("main")
    openai_tools = tool_manager.get_openai_tools()

    iteration = 0
    while iteration < max_iterations:
        iteration += 1
        logger.info(f"📍 Iteration {iteration}/{max_iterations}")

        try:
            # 获取上下文并调用模型
            context = memory.get_context()
            try:
                resp = await main_client.chat(context, tools=openai_tools)
            except TypeError:
                resp = await main_client.chat(context)

            content = resp.get("content", "")
            raw_response = resp.get("raw")

            # 解析 tool_calls（OpenAI 兼容格式）
            tool_calls = None
            if raw_response and hasattr(raw_response, "choices"):
                choice = raw_response.choices[0]
                if hasattr(choice.message, "tool_calls") and choice.message.tool_calls:
                    tool_calls = choice.message.tool_calls

            # 输出文本内容（如有）
            if content:
                logger.info(f"📝 模型返回文本，长度 {len(content)}")

                # 长响应自动缓存
                if len(content) > 5000:  # 超过5000字符
                    from services.file_store import cache_base64_data
                    import base64

                    response_id = cache_base64_data(
                        base64.b64encode(content.encode()).decode(),
                        file_type="text",
                        metadata={"length": len(content)}
                    )

                    # 添加缓存引用的消息
                    truncated_content = content[:500] + f"\n...[完整内容已缓存: {response_id}，使用 save_cached_file 工具可保存到本地]"
                    memory.add_message({"role": "assistant", "content": truncated_content})
                    logger.info(f"💾 长响应已缓存: {response_id}")
                else:
                    # 短响应直接保存
                    memory.add_message({"role": "assistant", "content": content})

                chunk_size = 1000
                for i in range(0, len(content), chunk_size):
                    yield {"type": "content", "data": content[i : i + chunk_size]}

            # 判断是否需要结束
            if not tool_calls:
                logger.info(f"🏁 无工具调用，任务结束 (iteration={iteration})")
                if content:
                    # 如果还没添加消息（长响应缓存时已添加），则添加
                    if len(content) <= 5000:
                        pass  # 已在上面添加过了

                # 保存对话到磁盘
                memory.save_to_disk()
                logger.info(f"💾 对话已保存: session_id={memory.session_id}")

                # 尝试提炼"用户偏好"写入 Markdown（仅当前端明确请求时）
                try:
                    if save_ltm:  # 只有前端明确传递 save_ltm=True 时才自动提炼
                        ltm = LTMMarkdown()
                        pref = await ltm.summarize_preferences(memory.get_context())
                        if pref and pref.strip():
                            ltm.append_section("用户偏好总结", pref, tags=["preference"])
                            yield {"type": "meta", "data": {"ltm_saved": True, "path": ltm.path, "kind": "preferences"}}
                        else:
                            yield {"type": "meta", "data": {"ltm_saved": False, "reason": "empty_summary"}}
                except Exception as _e:
                    logger.warning(f"LTM 写入失败: {_e}")

                break

            # 有工具调用，执行工具
            yield {"type": "tool_call", "data": {"message": f"正在调用{len(tool_calls)}个工具.."}}

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
            memory.add_message(assistant_msg)

            tool_call_dicts = [
                {
                    "id": tc.id,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in tool_calls
            ]

            tool_results = await tool_manager.execute_tool_calls(tool_call_dicts, session_id=memory.session_id)  # ✅ 传递session_id

            # 【关键修复】收集工具返回的图片file_id，注入到下一轮对话
            next_round_images = []

            for tool_result in tool_results:
                tool_name = tool_result.get("name", "unknown")

                # 🔑 核心优化：检测SubAgent报告并特殊处理
                is_subagent_report = tool_name.endswith("_subagent")

                if is_subagent_report:
                    # SubAgent报告处理逻辑
                    subagent_report = await _process_subagent_report(tool_result, next_round_images)

                    # 注入紧凑报告到记忆
                    memory.add_message(subagent_report["memory_message"])

                    # 返回格式化报告给前端
                    yield {
                        "type": "tool_result",
                        "data": {
                            "tool": tool_name,
                            "result": subagent_report["user_message"],
                        },
                    }
                else:
                    # 普通工具处理逻辑（保持原有逻辑）
                    truncated_result = _truncate_large_tool_result(tool_result)

                    # 检查file_id，如果是图片则准备注入
                    try:
                        result_content = json.loads(tool_result.get("content", "{}"))
                        if isinstance(result_content, dict) and not result_content.get("error", False):
                            data = result_content.get("data", {})
                            if isinstance(data, dict) and "file_id" in data:
                                fid = data["file_id"]
                                file_path = get_file_path_by_id(fid)

                                if file_path and is_image_file(file_path):
                                    image_data = get_image_as_base64(fid)
                                    if image_data:
                                        next_round_images.append({
                                            "type": "image_url",
                                            "image_url": {
                                                "url": image_data["url"]
                                            }
                                        })
                                        logger.info(f"📸 检测到截图 file_id: {fid}，将在下一轮注入到对话中")
                    except Exception as e:
                        logger.debug(f"解析工具结果时出错（可忽略）: {e}")

                    # 注入到记忆
                    memory.add_message(truncated_result)

                    # 返回给前端
                    yield {
                        "type": "tool_result",
                        "data": {
                            "tool": tool_name,
                            "result": tool_result.get("content", ""),
                        },
                    }

            # 【关键修复】如果有截图，将其注入到下一轮对话中供模型分析
            if next_round_images:
                screenshot_message = {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "📸 这是刚才工具执行后的截图，请分析页面内容："
                        }
                    ] + next_round_images
                }
                memory.add_message(screenshot_message)
                logger.info(f"✅ 已注入 {len(next_round_images)} 张截图到对话中，模型可以在下一轮分析")

        except Exception as e:
            logger.error(f"❌ Iteration {iteration} 异常: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            yield {"type": "content", "data": f"\n\n❌ 执行异常 (Iteration {iteration}): {str(e)}\n"}
            break

    # 达到最大迭代次数，也尝试提炼一次（仅当前端明确请求时）
    if iteration >= max_iterations:
        import logging as _logging
        _logging.getLogger(__name__).warning(
            f"⚠️ 达到最大迭代次数上限({max_iterations})，循环提前退出"
        )
        yield {
            "type": "content",
            "data": f"\n\n⚠️ 任务未完成：达到最大迭代次数({max_iterations})，可尝试增加 max_iterations 参数\n",
        }

        # 保存对话到磁盘
        memory.save_to_disk()
        logger.info(f"💾 对话已保存: session_id={memory.session_id}")

        try:
            if save_ltm:  # 只有前端明确传递 save_ltm=True 时才提炼
                ltm = LTMMarkdown()
                pref = await ltm.summarize_preferences(memory.get_context())
                if pref and pref.strip():
                    ltm.append_section("用户偏好总结", pref, tags=["preference"])
                    yield {"type": "meta", "data": {"ltm_saved": True, "path": ltm.path, "kind": "preferences"}}
        except Exception:
            pass

    yield {"type": "done"}
