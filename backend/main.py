"""
FastAPI 应用入口。

提供：
- GET /health       健康检查
- POST /chat        触发 Agent 主循环（StreamingResponse）

运行方式：
    uvicorn main:app --host 0.0.0.0 --port 7878 --reload
或读取 .env 中 HOST/PORT：
    python -m uvicorn main:app --host %HOST% --port %PORT%
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any, AsyncGenerator, Dict, List, Optional

from dotenv import load_dotenv, set_key, dotenv_values
from fastapi import FastAPI, File, Form, UploadFile, Body, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from core.agent_loop import agent_main_loop
from core.memory import MemoryManager
from core.model_manager import model_manager
from schemas.openai import ChatCompletionRequest
from schemas.todo import TodoCreate, TodoUpdate
from schemas.preferences import ExtractPreferencesRequest
from services.todo_store import (
    list_todos,
    create_todo,
    update_todo,
    delete_todo,
    reorder_todos,
)
from services.file_store import save_upload, get_file_content_by_id

load_dotenv()

app = FastAPI(title="七海-后端", version="1.0.0")


# CORS 配置
cors_origins = os.getenv("CORS_ORIGINS", "*")
origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"status": "ok"}


@app.post("/chat")
async def chat_endpoint(
    input: str = Form(..., description="用户输入"),
    files: Optional[List[UploadFile]] = None,
    save_ltm: bool = Form(False, description="是否保存长期记忆（用户偏好）"),
    messages: Optional[str] = Form(None, description="历史消息JSON字符串（前端传递）"),
    session_id: Optional[str] = Form(None, description="会话ID（前端对话窗口ID，用于TODO和记忆隔离）")
) -> StreamingResponse:
    """触发 Agent 主循环，返回流式文本。

    核心修改：接收前端传递的 session_id，实现对话窗口级别的上下文持久化
    """

    # 将上传文件暂存并传递文件路径列表
    file_ids: List[str] = []
    if files:
        tmp_dir = os.path.join(os.getcwd(), ".tmp_uploads")
        os.makedirs(tmp_dir, exist_ok=True)
        for f in files:
            content = await f.read()
            fid = save_upload(f.filename, content)
            file_ids.append(fid)

    # 解析历史消息
    history_messages: Optional[List[Dict[str, Any]]] = None
    if messages:
        try:
            import json
            history_messages = json.loads(messages)
        except Exception as e:
            print(f"⚠️ 解析历史消息失败: {e}")
            history_messages = None

    async def event_stream() -> AsyncGenerator[bytes, None]:
        try:
            # 核心修改：传递 session_id 给 agent_main_loop，实现对话窗口级别的上下文持久化
            async for chunk in agent_main_loop(
                input,
                file_ids or None,
                save_ltm=save_ltm,
                history_messages=history_messages,
                session_id=session_id  # 传递会话ID
            ):
                chunk_type = chunk.get("type")

                if chunk_type == "content":
                    yield chunk["data"].encode("utf-8")

                elif chunk_type == "meta":
                    # 可根据需要，将元信息以前缀形式输出
                    meta = chunk.get("data")
                    yield (f"\n[meta] {meta}\n").encode("utf-8")

                elif chunk_type == "tool_call":
                    # 输出工具调用信息
                    tool_info = chunk.get("data", {})
                    yield (f"\n[🔧 {tool_info.get('message', '工具调用')}]\n").encode("utf-8")

                elif chunk_type == "tool_result":
                    # 输出工具执行结果
                    data = chunk.get("data", {})
                    tool_name = data.get("tool", "unknown")
                    result = data.get("result", "")
                    # 追加一份规范格式的工具结果行，确保前端能解析并保留换行
                    try:
                        result_preview = result[:2000] + "..." if len(result) > 2000 else result
                        _formatted = f"\n[✓ {tool_name}]: {result_preview}\n"
                        yield _formatted.encode("utf-8")
                    except Exception:
                        pass
                    # 截断过长的结果
                    result_preview = result[:2000] + "..." if len(result) > 2000 else result
                    yield (f"\n[✓ {tool_name}]: {result_preview}\n").encode("utf-8")

                elif chunk_type == "done":
                    break

                await asyncio.sleep(0)  # 让出事件循环
        except Exception as e:
            # 捕获并输出异常信息
            import traceback
            error_msg = f"\n\n❌ Agent循环异常: {str(e)}\n{traceback.format_exc()}\n"
            print(error_msg)  # 打印到控制台
            yield error_msg.encode("utf-8")

    return StreamingResponse(event_stream(), media_type="text/plain; charset=utf-8")


# OpenAI Chat Completions 兼容端点
@app.post("/v1/chat/completions")
async def chat_completions(payload: ChatCompletionRequest = Body(...)):
    # 将上传文件引用形如 [file:ID] 的内容解析并注入独立消息
    messages = [m.model_dump() for m in payload.messages]

    # 注入：检测消息中的 [file:...] 标记
    injected: List[dict] = []
    for msg in messages:
        content = msg.get("content") or ""
        idx = 0
        while True:
            start = content.find("[file:", idx)
            if start == -1:
                break
            end = content.find("]", start)
            if end == -1:
                break
            fid = content[start + 6 : end]
            fcontent = get_file_content_by_id(fid)
            if fcontent:
                injected.append({"role": "system", "content": f"[附件:{fid}]\n{fcontent[:20000]}"})
            idx = end + 1

    mm = MemoryManager()
    if injected:
        mm.load_messages(injected)
    mm.load_messages(messages)
    compact_meta = await mm.check_and_compact()
    context = mm.get_context()

    client = model_manager.get_model("main")
    resp = await client.chat(context, override_model=payload.model)
    text = resp.get("content") if isinstance(resp, dict) else str(resp)
    if text is None:
        text = ""

    import time as _time
    result = {
        "id": f"chatcmpl-{int(_time.time()*1000)}",
        "object": "chat.completion",
        "created": int(_time.time()),
        "model": payload.model or model_manager.get_profile("main").model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "_meta": {"compact": compact_meta},
    }
    return JSONResponse(content=result)


# 上传端点：返回文件ID列表
@app.post("/upload")
async def upload_endpoint(files: List[UploadFile] = File(...)):
    ids: List[str] = []
    for f in files:
        content = await f.read()
        fid = save_upload(f.filename, content)
        ids.append(fid)
    return {"ids": ids}


# ToDo 清单 API（内置核心功能）
@app.get("/todos")
async def api_list_todos(session_id: Optional[str] = Query(None, description="会话ID，用于按会话隔离ToDo")):
    sid = session_id or "default"
    return [t.model_dump() for t in list_todos(session_id=sid)]


@app.post("/todos")
async def api_create_todo(
    payload: TodoCreate,
    session_id: Optional[str] = Query(None, description="会话ID，用于按会话隔离ToDo")
):
    sid = session_id or "default"
    return create_todo(payload, session_id=sid).model_dump()


@app.patch("/todos/{todo_id}")
async def api_update_todo(
    todo_id: str,
    payload: TodoUpdate,
    session_id: Optional[str] = Query(None, description="会话ID，用于按会话隔离ToDo")
):
    t = update_todo(todo_id, payload, session_id=session_id or "default")
    if not t:
        raise HTTPException(status_code=404, detail="Todo 不存在")
    return t.model_dump()


@app.delete("/todos/{todo_id}")
async def api_delete_todo(
    todo_id: str,
    session_id: Optional[str] = Query(None, description="会话ID，用于按会话隔离ToDo")
):
    ok = delete_todo(todo_id, session_id=session_id or "default")
    if not ok:
        raise HTTPException(status_code=404, detail="Todo 不存在")
    return {"deleted": True}


@app.post("/todos/reorder")
async def api_reorder_todos(
    order: List[str] = Body(..., embed=True),
    session_id: Optional[str] = Query(None, description="会话ID，用于按会话隔离ToDo")
):
    return [t.model_dump() for t in reorder_todos(order, session_id=session_id or "default")]


# 长期记忆提取端点（用于前端"保存偏好"按钮）
@app.post("/extract_preferences")
async def extract_preferences_endpoint(
    request: ExtractPreferencesRequest
) -> JSONResponse:
    """从对话历史中提取用户偏好并保存到长期记忆

    Args:
        request: 包含对话历史的请求对象，格式：{"messages": [{"role": "user|assistant", "content": "..."}]}

    Returns:
        JSON响应，包含提取的偏好内容和保存路径
    """
    try:
        from core.ltm import LTMMarkdown
        from datetime import datetime

        # 验证消息格式
        if not request.messages or len(request.messages) < 2:
            return JSONResponse(
                content={
                    "success": False,
                    "error": "对话历史过少，至少需要2条消息"
                },
                status_code=400
            )

        # 创建LTM实例并提取偏好
        ltm = LTMMarkdown()
        preferences = await ltm.summarize_preferences(request.messages)

        if preferences and preferences.strip():
            # 保存到Markdown文件
            ltm.append_section("用户偏好总结", preferences, tags=["preference"])

            return JSONResponse(content={
                "success": True,
                "preferences": preferences,
                "path": ltm.path,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        else:
            return JSONResponse(
                content={
                    "success": False,
                    "error": "无法提炼有效偏好：对话内容不包含明确的用户偏好信息"
                },
                status_code=400
            )

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"❌ 偏好提取失败: {error_detail}")

        return JSONResponse(
            content={
                "success": False,
                "error": f"提取失败: {str(e)}"
            },
            status_code=500
        )


@app.get("/api/settings")
async def get_settings():
    env_path = os.path.join(os.getcwd(), ".env")
    if not os.path.exists(env_path):
        raise HTTPException(status_code=404, detail=".env 文件不存在")

    try:
        env_values = dotenv_values(env_path)
        return JSONResponse(content={
            "MAIN_PROVIDER": env_values.get("MAIN_PROVIDER", ""),
            "MAIN_MODEL": env_values.get("MAIN_MODEL", ""),
            "MAIN_API_KEY": env_values.get("MAIN_API_KEY", ""),
            "MAIN_BASE_URL": env_values.get("MAIN_BASE_URL", ""),
            "MAIN_CONTEXT_LENGTH": env_values.get("MAIN_CONTEXT_LENGTH", ""),
            "COMPACT_PROVIDER": env_values.get("COMPACT_PROVIDER", ""),
            "COMPACT_MODEL": env_values.get("COMPACT_MODEL", ""),
            "COMPACT_API_KEY": env_values.get("COMPACT_API_KEY", ""),
            "COMPACT_BASE_URL": env_values.get("COMPACT_BASE_URL", ""),
            "COMPACT_CONTEXT_LENGTH": env_values.get("COMPACT_CONTEXT_LENGTH", ""),
            "QUICK_PROVIDER": env_values.get("QUICK_PROVIDER", ""),
            "QUICK_MODEL": env_values.get("QUICK_MODEL", ""),
            "QUICK_API_KEY": env_values.get("QUICK_API_KEY", ""),
            "QUICK_BASE_URL": env_values.get("QUICK_BASE_URL", ""),
            "QUICK_CONTEXT_LENGTH": env_values.get("QUICK_CONTEXT_LENGTH", ""),
            "SEARCH_AGENT_PROVIDER": env_values.get("SEARCH_AGENT_PROVIDER", ""),
            "SEARCH_AGENT_MODEL": env_values.get("SEARCH_AGENT_MODEL", ""),
            "SEARCH_AGENT_API_KEY": env_values.get("SEARCH_AGENT_API_KEY", ""),
            "SEARCH_AGENT_BASE_URL": env_values.get("SEARCH_AGENT_BASE_URL", ""),
            "SEARCH_AGENT_CONTEXT_LENGTH": env_values.get("SEARCH_AGENT_CONTEXT_LENGTH", ""),
            "BROWSER_AGENT_PROVIDER": env_values.get("BROWSER_AGENT_PROVIDER", ""),
            "BROWSER_AGENT_MODEL": env_values.get("BROWSER_AGENT_MODEL", ""),
            "BROWSER_AGENT_API_KEY": env_values.get("BROWSER_AGENT_API_KEY", ""),
            "BROWSER_AGENT_BASE_URL": env_values.get("BROWSER_AGENT_BASE_URL", ""),
            "BROWSER_AGENT_CONTEXT_LENGTH": env_values.get("BROWSER_AGENT_CONTEXT_LENGTH", ""),
            "WINDOWS_AGENT_PROVIDER": env_values.get("WINDOWS_AGENT_PROVIDER", ""),
            "WINDOWS_AGENT_MODEL": env_values.get("WINDOWS_AGENT_MODEL", ""),
            "WINDOWS_AGENT_API_KEY": env_values.get("WINDOWS_AGENT_API_KEY", ""),
            "WINDOWS_AGENT_BASE_URL": env_values.get("WINDOWS_AGENT_BASE_URL", ""),
            "WINDOWS_AGENT_CONTEXT_LENGTH": env_values.get("WINDOWS_AGENT_CONTEXT_LENGTH", ""),
            "TAVILY_API_KEY": env_values.get("TAVILY_API_KEY", ""),
            "WORKSPACE_ROOT": env_values.get("WORKSPACE_ROOT", ""),
            "PORT": env_values.get("PORT", ""),
            "AUTO_COMPACT_RATIO": env_values.get("AUTO_COMPACT_RATIO", ""),
            "LTM_MD_PATH": env_values.get("LTM_MD_PATH", ""),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取设置失败: {str(e)}")


@app.post("/api/settings")
async def update_settings(settings: Dict[str, str] = Body(...)):
    env_path = os.path.join(os.getcwd(), ".env")
    if not os.path.exists(env_path):
        raise HTTPException(status_code=404, detail=".env 文件不存在")

    try:
        for key, value in settings.items():
            set_key(env_path, key, value)

        load_dotenv(override=True)

        return JSONResponse(content={
            "success": True,
            "message": "设置已保存，部分设置可能需要重启后端服务才能生效"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存设置失败: {str(e)}")


@app.post("/api/models")
async def get_models(payload: Dict[str, str] = Body(...)):
    """获取指定API提供商的模型列表"""
    base_url = payload.get("baseUrl", "").strip()
    api_key = payload.get("apiKey", "").strip()

    if not base_url or not api_key:
        raise HTTPException(status_code=400, detail="Base URL 和 API Key 不能为空")

    try:
        from httpx import AsyncClient

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        async with AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{base_url.rstrip('/')}/v1/models",
                headers=headers
            )

            if not response.status_code == 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"获取模型列表失败: {response.text}"
                )

            data = response.json()
            models = data.get("data", [])

            return JSONResponse(content={
                "models": [{"id": m["id"], "object": m.get("object", "model")} for m in models]
            })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"连接失败: {str(e)}"
        )


@app.get("/v1/models")
async def list_models(base_url: Optional[str] = Query(None, description="API基础URL")):
    """OpenAI兼容的模型列表端点

    支持两种方式：
    1. 通过Authorization头传递Bearer token和base_url查询参数
    2. 从环境变量读取MAIN_BASE_URL和MAIN_API_KEY
    """
    import sys

    from httpx import AsyncClient

    # 方式1：优先使用请求头中的Authorization和query中的base_url
    auth_header = None
    request_base_url = base_url

    # 从环境变量获取默认值（方式2）
    default_base_url = os.getenv("MAIN_BASE_URL", "").strip()
    default_api_key = os.getenv("MAIN_API_KEY", "").strip()

    print(f"🔍 [STDERR] query base_url: {base_url}", file=sys.stderr)
    print(f"🔍 [STDERR] env MAIN_BASE_URL: {default_base_url}", file=sys.stderr)
    print(f"🔍 [STDERR] env MAIN_API_KEY: {default_api_key[:20] if default_api_key else 'None'}...", file=sys.stderr, flush=True)

    # 确定使用的base_url
    target_base_url = request_base_url or default_base_url

    if not target_base_url:
        print(f"❌ [STDERR] 缺少base_url", file=sys.stderr, flush=True)
        raise HTTPException(
            status_code=400,
            detail="缺少base_url参数，且未配置MAIN_BASE_URL环境变量"
        )

    # 确定使用的API key
    api_key = default_api_key

    if not api_key:
        print(f"❌ [STDERR] 缺少API Key", file=sys.stderr, flush=True)
        raise HTTPException(
            status_code=400,
            detail="缺少API Key，且未配置MAIN_API_KEY环境变量"
        )

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # 修复：target_base_url已经包含/v1，只需追加models
        target_url = f"{target_base_url.rstrip('/')}/models"
        print(f"🔍 [STDERR] 准备请求模型列表", file=sys.stderr)
        print(f"   [STDERR] URL: {target_url}", file=sys.stderr, flush=True)
        print(f"   [STDERR] Headers: {headers}", file=sys.stderr, flush=True)

        # 修复：使用最简配置，参考模型管理器的httpx客户端配置
        # 这避免了复杂的连接池和HTTP/2可能导致的兼容性问题
        import httpx
        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            http2=False,
            follow_redirects=True
        )
        async with http_client as client:
            print(f"🔍 [STDERR] 发送GET请求 (简化配置)...", file=sys.stderr, flush=True)
            response = await client.get(target_url, headers=headers)
            print(f"🔍 [STDERR] 响应状态: {response.status_code}", file=sys.stderr, flush=True)
            print(f"🔍 [STDERR] 响应内容: {response.text[:500]}", file=sys.stderr, flush=True)

            if response.status_code == 401:
                raise HTTPException(
                    status_code=401,
                    detail="API Key无效或已过期"
                )
            elif response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="模型列表端点不存在，请检查base_url是否正确"
                )
            elif not response.status_code == 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"获取模型列表失败: {response.text}"
                )

            return JSONResponse(content=response.json())

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"连接失败: {str(e)}"
        )


@app.post("/api/clear_all_cache")
async def clear_all_cache():
    """清除所有缓存数据：对话记录、TODO、上传文件"""
    try:
        import shutil
        from pathlib import Path

        results = {
            "conversations_cleared": False,
            "todos_cleared": False,
            "uploads_cleared": False,
            "errors": []
        }

        # 1. 清除对话记录
        try:
            conversations_dir = Path(os.getcwd()) / "data" / "conversations"
            if conversations_dir.exists():
                shutil.rmtree(conversations_dir)
                conversations_dir.mkdir(parents=True, exist_ok=True)
                results["conversations_cleared"] = True
        except Exception as e:
            results["errors"].append(f"清除对话记录失败: {str(e)}")

        # 2. 清除TODO（会话化存储目录 data/todos/ 下的全部会话文件）
        try:
            todos_dir = Path(os.getcwd()) / "data" / "todos"
            if todos_dir.exists():
                import shutil as _shutil
                _shutil.rmtree(todos_dir)
            todos_dir.mkdir(parents=True, exist_ok=True)
            results["todos_cleared"] = True
        except Exception as e:
            results["errors"].append(f"清除TODO失败: {str(e)}")

        # 3. 清除上传文件（缓存的截图等）
        try:
            uploads_dir = Path(os.getcwd()) / "data" / "uploads"
            uploads_index = Path(os.getcwd()) / "data" / "uploads.index"

            if uploads_dir.exists():
                # 删除所有文件
                for file in uploads_dir.iterdir():
                    if file.is_file():
                        file.unlink()
                results["uploads_cleared"] = True

            # 清空索引
            if uploads_index.exists():
                with open(uploads_index, "w", encoding="utf-8") as f:
                    f.write("")

        except Exception as e:
            results["errors"].append(f"清除上传文件失败: {str(e)}")

        # 检查是否全部成功
        all_success = (
            results["conversations_cleared"] and
            results["todos_cleared"] and
            results["uploads_cleared"] and
            len(results["errors"]) == 0
        )

        if all_success:
            return JSONResponse(content={
                "success": True,
                "message": "✅ 所有缓存已清除！包括对话记录、TODO列表和缓存文件。",
                "details": results
            })
        else:
            return JSONResponse(
                content={
                    "success": False,
                    "message": "⚠️ 部分缓存清除失败",
                    "details": results
                },
                status_code=207  # Multi-Status
            )

    except Exception as e:
        import traceback
        return JSONResponse(
            content={
                "success": False,
                "message": f"清除缓存失败: {str(e)}",
                "traceback": traceback.format_exc()
            },
            status_code=500
        )


@app.post("/generate_title")
async def generate_title(messages: List[Dict[str, str]] = Body(...)):
    """使用轻量化模型生成对话标题

    Args:
        messages: 对话历史，格式：[{"role": "user|assistant", "content": "..."}]

    Returns:
        JSON响应，包含生成的标题
    """
    try:
        if not messages or len(messages) == 0:
            return JSONResponse(
                content={"success": False, "error": "消息列表为空"},
                status_code=400
            )

        compact_client = model_manager.get_model("compact")

        prompt_messages = [
            {
                "role": "system",
                "content": "你是一个标题生成助手。请根据对话内容，生成一个简洁、准确的标题（不超过15个字）。只输出标题文本，不要有任何解释或标点符号。"
            }
        ]

        conversation_text = "\n".join([
            f"{msg['role']}: {msg['content'][:200]}"
            for msg in messages[:4]
        ])

        prompt_messages.append({
            "role": "user",
            "content": f"请为以下对话生成标题：\n{conversation_text}"
        })

        resp = await compact_client.chat(prompt_messages)
        title = resp.get("content", "").strip() if isinstance(resp, dict) else str(resp).strip()

        if not title:
            title = messages[0]["content"][:30] + ("..." if len(messages[0]["content"]) > 30 else "")

        title = title.replace('"', '').replace("'", '').strip()
        if len(title) > 30:
            title = title[:30] + "..."

        return JSONResponse(content={
            "success": True,
            "title": title
        })

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"❌ 标题生成失败: {error_detail}")

        fallback_title = messages[0]["content"][:30] + ("..." if len(messages[0]["content"]) > 30 else "") if messages else "新对话"

        return JSONResponse(
            content={
                "success": False,
                "error": f"生成失败: {str(e)}",
                "title": fallback_title
            },
            status_code=200
        )

    
# =============== SSE: TODO 实时推送 ===============
@app.get("/todos/stream")
async def todos_stream(session_id: Optional[str] = Query(None, description="会话ID，用于按会话隔离ToDo")) -> StreamingResponse:
    """基于SSE的TODO实时推送。

    - 首次连接发送当前列表
    - 之后按 session 文件 mtime 变化推送
    - 每秒发送一条 keepalive 注释，保持连接
    """

    sid = session_id or "default"

    async def sse_events() -> AsyncGenerator[bytes, None]:
        import asyncio as _asyncio
        import json as _json
        import os as _os
        from pathlib import Path as _Path
        from services.todo_store import list_todos

        data_dir = _Path(_os.getcwd()) / "data" / "todos"
        data_dir.mkdir(parents=True, exist_ok=True)
        session_file = data_dir / f"{sid}.json"

        last_payload = None
        last_mtime = None

        # 初始推送
        try:
            todos = [t.model_dump() for t in list_todos(session_id=sid)]
            payload = _json.dumps({"todos": todos}, ensure_ascii=False)
            last_payload = payload
            yield f"event: todos\n".encode("utf-8")
            yield f"data: {payload}\n\n".encode("utf-8")
        except Exception:
            pass

        while True:
            try:
                cur_mtime = session_file.stat().st_mtime if session_file.exists() else None
                if cur_mtime != last_mtime:
                    last_mtime = cur_mtime
                    todos = [t.model_dump() for t in list_todos(session_id=sid)]
                    payload = _json.dumps({"todos": todos}, ensure_ascii=False)
                    if payload != last_payload:
                        last_payload = payload
                        yield f"event: todos\n".encode("utf-8")
                        yield f"data: {payload}\n\n".encode("utf-8")

                yield f": keepalive {sid}\n\n".encode("utf-8")
                await _asyncio.sleep(1.0)
            except _asyncio.CancelledError:
                break
            except Exception:
                await _asyncio.sleep(1.5)

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(sse_events(), media_type="text/event-stream", headers=headers)

# 便捷运行：python main.py
if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "7878"))

    config = uvicorn.Config(
        "main:app",
        host=host,
        port=port,
        reload=True,
        loop="asyncio",
        reload_delay=0.25
    )

    server = uvicorn.Server(config)
    asyncio.run(server.serve())
