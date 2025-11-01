"""
使用httpx替换OpenAI SDK的自定义客户端

解决CF盾拦截问题的核心方案:
1. 使用httpx直接发送HTTP请求,避免OpenAI SDK的指纹特征
2. 模拟浏览器请求头,绕过CF盾检测
3. 实现与OpenAI SDK兼容的接口
"""
import httpx
import json
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ChatCompletionChoice:
    index: int
    message: Dict[str, Any]
    finish_reason: str


@dataclass
class ChatCompletionUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class ChatCompletion:
    id: str
    object: str
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: ChatCompletionUsage


class HttpxOpenAIClient:
    """使用httpx实现的OpenAI兼容客户端,绕过CF盾"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 600.0,
        max_retries: int = 3
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries

        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin"
        }

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            http2=True,
            follow_redirects=True
        )

    async def chat_completions_create(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.2,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs
    ) -> ChatCompletion:
        """创建聊天补全请求"""

        url = f"{self.base_url}/chat/completions"

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

        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(
                    url,
                    headers=self.headers,
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()

                    choices = [
                        ChatCompletionChoice(
                            index=choice["index"],
                            message=choice["message"],
                            finish_reason=choice.get("finish_reason", "stop")
                        )
                        for choice in data["choices"]
                    ]

                    usage = ChatCompletionUsage(
                        prompt_tokens=data["usage"]["prompt_tokens"],
                        completion_tokens=data["usage"]["completion_tokens"],
                        total_tokens=data["usage"]["total_tokens"]
                    )

                    return ChatCompletion(
                        id=data["id"],
                        object=data["object"],
                        created=data["created"],
                        model=data["model"],
                        choices=choices,
                        usage=usage
                    )

                elif response.status_code in [502, 503, 429]:
                    if attempt < self.max_retries - 1:
                        import asyncio
                        await asyncio.sleep(2 ** attempt)
                        continue
                    else:
                        raise Exception(f"HTTP {response.status_code}: {response.text}")

                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")

            except httpx.TimeoutException:
                if attempt < self.max_retries - 1:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    raise Exception("Request timeout")

            except Exception as e:
                if attempt < self.max_retries - 1:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    raise e

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
