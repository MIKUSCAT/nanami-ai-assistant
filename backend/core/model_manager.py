"""
多模型管理器（ModelManager）

目标：
- 统一管理不同用途（main/quick/task/reasoning）的模型配置与获取
- 支持 OpenAI 兼容 API（可通过 base_url 定向到私有或第三方推理服务）
- 暴露上下文长度、流式等能力参数，供记忆压缩与调度使用

设计参考：Kode-main/src/utils/model.ts - ModelManager
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class ModelProfile:
    """模型配置描述。

    - name: 指针名或配置名（如：main/quick/task/reasoning）
    - provider: 提供商标识（openai/azure/other），此处仅作标记
    - model: 实际调用的模型名（如 gpt-4o、gpt-4o-mini、o4-mini 等）
    - api_key: 对应服务的 API Key
    - base_url: OpenAI 兼容 API 的 base url，可为空走默认
    - context_length: 上下文窗口大小（token），用于触发压缩
    - extra: 其他扩展参数（如 reasoning 配置等）
    """

    name: str
    provider: str
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    context_length: int = 200_000
    extra: Dict[str, Any] = None


class LLMClient:
    """简单的 LLM 客户端封装，适配 OpenAI 兼容接口。

    仅实现最小可用：非流式聊天。

    特性：
    - 速率限制：通过 LLM_MIN_INTERVAL 环境变量控制请求间隔（秒）
    - 自动重试：通过 API_MAX_RETRIES 环境变量控制重试次数
    - 超时控制：通过 API_REQUEST_TIMEOUT 环境变量控制超时时间
    """

    # 类级别的速率限制器（跨实例共享，避免多个LLMClient绕过限制）
    _rate_limiter_lock = None  # 延迟初始化，避免事件循环问题
    _last_call_times: Dict[str, float] = {}  # {model_key: timestamp}

    def __init__(self, profile: ModelProfile):
        from core.httpx_openai_adapter import HttpxAsyncOpenAI
        import httpx
        import asyncio

        self.profile = profile
        # 如果未提供专用 key/base_url，回退到 OPENAI_*
        api_key = profile.api_key or os.getenv("OPENAI_API_KEY")
        base_url = profile.base_url or os.getenv("OPENAI_BASE_URL")

        # 配置超时时间（从环境变量读取，默认5分钟）
        # 考虑到工具执行可能需要较长时间（例如访问慢速网站），设置较长的超时
        try:
            timeout_seconds = float(os.getenv("API_REQUEST_TIMEOUT", "600"))
        except Exception:
            timeout_seconds = 600.0

        # 配置重试策略（指数退避）
        # 默认重试3次，对502/503错误特别有效
        try:
            max_retries = int(os.getenv("API_MAX_RETRIES", "3"))
        except Exception:
            max_retries = 3

        # 创建自定义 httpx 客户端，设置超时和浏览器标识
        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            http2=True,
            follow_redirects=True
        )

        # 使用自定义httpx客户端替代OpenAI SDK，绕过CF盾拦截
        # 完全兼容OpenAI SDK的接口和返回对象结构
        self.client = HttpxAsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=http_client,
            max_retries=max_retries,
            timeout=timeout_seconds
        )

    async def chat(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.2,
        override_model: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None
    ) -> Dict[str, Any]:
        """调用聊天补全，返回统一结构：{"content": str, "raw": 原始响应}。

        Args:
            messages: 形如 [{"role": "user"|"assistant"|"system", "content": "..."}]
            temperature: 温度参数
            override_model: 覆盖模型名称
            tools: OpenAI格式的工具定义列表
            tool_choice: 工具选择策略 ("auto", "required", "none")

        Returns:
            {"content": str, "raw": 原始响应对象}
        """
        # 速率限制：避免高频调用导致API 502错误
        await self._apply_rate_limit()

        try:
            # 构建请求参数
            request_params = {
                "model": (override_model or self.profile.model),
                "messages": messages,
                "temperature": temperature,
            }

            # 如果提供了工具定义，添加到请求中
            if tools:
                request_params["tools"] = tools
                # 使用传入的 tool_choice，默认为 "auto" 让模型自主判断
                if tool_choice:
                    request_params["tool_choice"] = tool_choice

            resp = await self.client.chat.completions.create(**request_params)

            content = resp.choices[0].message.content or ""
            return {"content": content, "raw": resp}
        except Exception as e:
            # 失败时返回可诊断信息
            return {"content": f"[LLM错误] {e}", "error": True}

    async def _apply_rate_limit(self) -> None:
        """应用速率限制，避免高频调用API导致502错误

        通过环境变量 LLM_MIN_INTERVAL 控制请求间隔（秒），默认0表示不限制。
        使用类级别的锁和时间戳字典，确保跨实例生效。
        """
        import asyncio
        import time

        # 延迟初始化锁（避免在模块加载时创建，可能导致事件循环问题）
        if LLMClient._rate_limiter_lock is None:
            LLMClient._rate_limiter_lock = asyncio.Lock()

        # 读取配置：最小请求间隔（秒）
        try:
            min_interval = float(os.getenv("LLM_MIN_INTERVAL", "0"))
        except Exception:
            min_interval = 0

        # 如果不限制，直接返回
        if min_interval <= 0:
            return

        # 生成模型唯一标识（base_url + model，避免不同API混淆）
        model_key = f"{self.profile.base_url or 'default'}:{self.profile.model}"

        async with LLMClient._rate_limiter_lock:
            last_time = LLMClient._last_call_times.get(model_key, 0)
            elapsed = time.time() - last_time

            # 如果距离上次调用不足最小间隔，等待
            if elapsed < min_interval:
                wait_time = min_interval - elapsed
                await asyncio.sleep(wait_time)

            # 更新最后调用时间
            LLMClient._last_call_times[model_key] = time.time()


class ModelManager:
    """多模型管理器。

    - 通过 env 加载四类指针模型：main/quick/task/reasoning
    - 提供 get_model(pointer) 返回 LLMClient
    - 提供 get_profile(pointer) 以便读取 context_length 等参数
    - 内置指针回退逻辑：未知指针 → main
    """

    def __init__(self) -> None:
        self.profiles: Dict[str, ModelProfile] = self._load_profiles_from_env()
        self.pointers: Dict[str, str] = {
            "main": "main",
            "compact": "compact",
            "quick": "quick",
            "task": "task",
            "reasoning": "reasoning",
            # SubAgent专用模型
            "search_agent": "search_agent",
            "browser_agent": "browser_agent",
            "windows_agent": "windows_agent",
        }

    def _load_profiles_from_env(self) -> Dict[str, ModelProfile]:
        def _int_env(name: str, default: int) -> int:
            try:
                return int(os.getenv(name, default))
            except Exception:
                return default

        # Helper: 读取单个 profile 组
        def read_group(prefix: str, fallback_model: str) -> ModelProfile:
            provider = os.getenv(f"{prefix}_PROVIDER", "openai").strip()
            model = os.getenv(f"{prefix}_MODEL", fallback_model).strip()
            api_key = os.getenv(f"{prefix}_API_KEY")
            base_url = os.getenv(f"{prefix}_BASE_URL")
            context_length = _int_env(f"{prefix}_CONTEXT_LENGTH", 200_000)
            return ModelProfile(
                name=prefix.lower(),
                provider=provider,
                model=model,
                api_key=api_key,
                base_url=base_url,
                context_length=context_length,
                extra={},
            )

        profiles = {
            "main": read_group("MAIN", "gpt-4o"),
            "compact": read_group("COMPACT", "gpt-4o-mini"),  # 压缩模型
            "quick": read_group("QUICK", "gpt-4o-mini"),
            "task": read_group("TASK", "gpt-4o-mini"),
            "reasoning": read_group("REASONING", "o4-mini"),
            # SubAgent专用模型
            "search_agent": read_group("SEARCH_AGENT", "gpt-4o-mini"),
            "browser_agent": read_group("BROWSER_AGENT", "gpt-4o-mini"),
            "windows_agent": read_group("WINDOWS_AGENT", "gpt-4o-mini"),
        }
        return profiles

    def get_profile(self, pointer: str) -> ModelProfile:
        key = self.pointers.get(pointer, self.pointers["main"])  # 回退到 main
        return self.profiles[key]

    def get_model(self, pointer: str) -> LLMClient:
        profile = self.get_profile(pointer)
        return LLMClient(profile)


# 单例，便于全局使用
model_manager = ModelManager()
