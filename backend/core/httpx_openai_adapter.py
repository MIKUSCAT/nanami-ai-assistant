"""
httpx实现的OpenAI SDK适配器 - 完全兼容原有接口

核心设计:
1. 保持与OpenAI SDK完全相同的接口和返回对象结构
2. 使用httpx绕过CF盾,模拟浏览器请求头
3. 零侵入式替换,无需修改任何调用代码
"""
import httpx
import json
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


class ToolCall:
    """模拟OpenAI SDK的ToolCall对象"""
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("id", "")
        self.type = data.get("type", "function")
        self.function = type('Function', (), {
            'name': data.get("function", {}).get("name", ""),
            'arguments': data.get("function", {}).get("arguments", "{}")
        })()


class Message:
    """模拟OpenAI SDK的Message对象"""
    def __init__(self, data: Dict[str, Any]):
        self.content = data.get("content")
        self.role = data.get("role", "assistant")

        tool_calls_data = data.get("tool_calls")
        if tool_calls_data:
            self.tool_calls = [ToolCall(tc) for tc in tool_calls_data]
        else:
            self.tool_calls = None


class Choice:
    """模拟OpenAI SDK的Choice对象"""
    def __init__(self, data: Dict[str, Any]):
        self.index = data.get("index", 0)
        self.message = Message(data.get("message", {}))
        self.finish_reason = data.get("finish_reason", "stop")


class Usage:
    """模拟OpenAI SDK的Usage对象"""
    def __init__(self, data: Dict[str, Any]):
        self.prompt_tokens = data.get("prompt_tokens", 0)
        self.completion_tokens = data.get("completion_tokens", 0)
        self.total_tokens = data.get("total_tokens", 0)


class ChatCompletion:
    """模拟OpenAI SDK的ChatCompletion对象"""
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("id", "")
        self.object = data.get("object", "chat.completion")
        self.created = data.get("created", 0)
        self.model = data.get("model", "")
        self.choices = [Choice(c) for c in data.get("choices", [])]
        self.usage = Usage(data.get("usage", {}))


class ChatCompletions:
    """模拟OpenAI SDK的chat.completions接口"""
    def __init__(self, client: 'HttpxAsyncOpenAI'):
        self.client = client

    async def create(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.2,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs
    ) -> ChatCompletion:
        """创建聊天补全 - 完全兼容OpenAI SDK接口"""

        url = f"{self.client.base_url}/chat/completions"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            **kwargs
        }

        if tools:
            payload["tools"] = tools
            if tool_choice:
                payload["tool_choice"] = tool_choice

        for attempt in range(self.client.max_retries):
            try:
                response = await self.client.http_client.post(
                    url,
                    headers=self.client.headers,
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    return ChatCompletion(data)

                elif response.status_code in [502, 503, 429]:
                    if attempt < self.client.max_retries - 1:
                        import asyncio
                        await asyncio.sleep(2 ** attempt)
                        continue
                    else:
                        raise Exception(f"HTTP {response.status_code}: {response.text}")

                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")

            except httpx.TimeoutException:
                if attempt < self.client.max_retries - 1:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    raise Exception("Request timeout")

            except Exception as e:
                if attempt < self.client.max_retries - 1:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    raise e


class Chat:
    """模拟OpenAI SDK的chat接口"""
    def __init__(self, client: 'HttpxAsyncOpenAI'):
        self.completions = ChatCompletions(client)


class HttpxAsyncOpenAI:
    """
    使用httpx实现的AsyncOpenAI完全兼容替代品

    特点:
    1. 接口与OpenAI SDK完全一致
    2. 返回对象结构与OpenAI SDK完全一致
    3. 使用浏览器User-Agent绕过CF盾
    4. 零侵入式替换,无需修改任何调用代码
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        http_client: Optional[httpx.AsyncClient] = None,
        max_retries: int = 3,
        timeout: Optional[float] = None
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.max_retries = max_retries

        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }

        if http_client:
            self.http_client = http_client
        else:
            timeout_config = httpx.Timeout(timeout) if timeout else None
            self.http_client = httpx.AsyncClient(
                timeout=timeout_config,
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                http2=True,
                follow_redirects=True
            )

        self.chat = Chat(self)

    async def close(self):
        """关闭客户端"""
        await self.http_client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
