"""Tavily 工具封装（使用官方 AsyncTavilyClient SDK）。

四个工具：
1. TavilySearchTool - 实时网页搜索（支持论文搜索、时间过滤、域名过滤）
2. TavilyExtractTool - 从URL提取内容
3. TavilyMapTool - 网站结构映射
4. TavilyCrawlTool - 网站爬取（Map + Extract 组合）
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from tavily import AsyncTavilyClient

from .base import BaseTool


class TavilySearchTool(BaseTool):
    """Tavily 实时网页搜索工具。

    适用场景：
    - 搜索学术论文（指定 arxiv.org、scholar.google.com 等域名）
    - 搜索最新新闻（设置 topic="news"，使用 days 过滤）
    - 搜索金融信息（设置 topic="finance"）

    参数说明：
    - query (str, 必需): 搜索查询词
        示例: "transformer architecture"
        示例: "quantum computing applications"

    - max_results (int, 可选): 返回结果数量，范围 1-20，默认 5
        示例: 10

    - search_depth (str, 可选): 搜索深度
        - "basic": 快速搜索，信用消耗 1/请求
        - "advanced": 深度搜索，更相关的内容片段，信用消耗 2/请求
        默认: "basic"

    - topic (str, 可选): 搜索主题，模型可根据意图选择
        - "general": 一般搜索（默认）
        - "news": 新闻搜索（用于实时事件）
        - "finance": 金融搜索
        默认: "general"

    - days (int, 可选): 过去N天内的结果（时间过滤）
        示例: 7 表示过去一周
        示例: 30 表示过去一个月
        注意: 仅对 topic="news" 有效

    - include_domains (list[str], 可选): 仅搜索指定域名（最多300个）
        示例: ["arxiv.org", "scholar.google.com"] 用于搜索论文
        示例: ["github.com"] 用于搜索代码

    使用示例:
        # 搜索最近的AI论文
        result = await tool.execute(
            query="attention mechanism in transformers",
            include_domains=["arxiv.org"],
            max_results=10,
            search_depth="advanced"
        )

        # 搜索最近7天的AI新闻
        result = await tool.execute(
            query="AI breakthrough",
            topic="news",
            days=7,
            max_results=5
        )
    """

    name = "tavily_search"
    description = "实时网页搜索，支持论文搜索（指定域名）、新闻搜索（时间过滤）、深度搜索。"

    def __init__(self) -> None:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            self.client = None
        else:
            self.client = AsyncTavilyClient(api_key=api_key)

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行搜索。

        返回格式:
            成功: {"error": False, "data": {...}}
            失败: {"error": True, "message": "错误信息"}
        """
        if self.client is None:
            return {"error": True, "message": "未配置 TAVILY_API_KEY"}

        query = kwargs.get("query") or kwargs.get("q")
        if not query:
            return {"error": True, "message": "缺少搜索词 query"}

        search_params = {"query": query}

        search_params["max_results"] = kwargs.get("max_results", 7)
        search_params["search_depth"] = kwargs.get("search_depth", "advanced")

        if kwargs.get("topic") is not None:
            search_params["topic"] = kwargs["topic"]

        if kwargs.get("days") is not None:
            search_params["days"] = kwargs["days"]

        if kwargs.get("include_domains") is not None:
            search_params["include_domains"] = kwargs["include_domains"]

        try:
            result = await self.client.search(**search_params)
            return {"error": False, "data": result}
        except Exception as e:
            return {"error": True, "message": f"Tavily Search 调用失败: {e}"}

    def get_openai_definition(self) -> Dict[str, Any]:
        """返回OpenAI Function Calling定义，供SubAgent调用。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "调用 Tavily Search 执行深度网页检索，支持官方站点筛选与时间过滤。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索查询语句，支持 site:example.com 语法锁定官网或知名站点。"
                        },
                        "auto_parameters": {
                            "type": "boolean",
                            "description": "是否启用 Tavily 自动参数优化（Beta）。"
                        },
                        "topic": {
                            "type": "string",
                            "enum": ["general", "news", "finance"],
                            "description": "主题模式；news 更关注最新资讯。"
                        },
                        "search_depth": {
                            "type": "string",
                            "enum": ["basic", "advanced"],
                            "description": "搜索深度，深度研究时必须使用 advanced。"
                        },
                        "chunks_per_source": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 3,
                            "description": "每个结果的内容块数量，范围 1-3。"
                        },
                        "max_results": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 20,
                            "description": "返回的最大结果数，深度搜索建议 10-15。"
                        },
                        "time_range": {
                            "type": "string",
                            "enum": ["day", "week", "month", "year", "d", "w", "m", "y"],
                            "description": "相对时间范围过滤，例如 week 或 m。"
                        },
                        "days": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 30,
                            "description": "最近 N 天的结果，仅 topic=news 时生效。"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "起始日期，格式 YYYY-MM-DD。"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "结束日期，格式 YYYY-MM-DD。"
                        },
                        "include_domains": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "仅保留的域名列表，用于锁定官网与知名网站（最多 300 个）。"
                        },
                        "exclude_domains": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "需要排除的域名列表（最多 150 个）。"
                        },
                        "country": {
                            "type": "string",
                            "description": "可选国家或地区过滤，例如 us、uk、cn。"
                        },
                        "include_answer": {
                            "anyOf": [
                                {"type": "boolean"},
                                {"type": "string", "enum": ["basic", "advanced"]}
                            ],
                            "description": "是否返回 Tavily 自动撰写的回答，可填写 true/basic/advanced。"
                        },
                        "include_raw_content": {
                            "type": "string",
                            "enum": ["markdown", "text"],
                            "description": "是否附加原文内容，支持 markdown 或 text。"
                        },
                        "include_images": {
                            "type": "boolean",
                            "description": "是否包含相关图片链接。"
                        },
                        "include_image_descriptions": {
                            "type": "boolean",
                            "description": "是否包含图片描述（需 include_images 为 true）。"
                        },
                        "include_favicon": {
                            "type": "boolean",
                            "description": "是否返回站点图标 URL。"
                        }
                    },
                    "required": ["query"]
                }
            }
        }


class TavilyExtractTool(BaseTool):
    """Tavily 内容提取工具。

    适用场景：
    - 从学术论文URL提取正文内容
    - 从网页提取结构化内容（包括表格）
    - 批量提取多个URL的内容

    参数说明：
    - urls (list[str], 必需): 要提取的 URL 列表，最多 20 个
        示例: ["https://arxiv.org/abs/1706.03762"]
        示例: ["https://example.com/page1", "https://example.com/page2"]

    - extract_depth (str, 可选): 提取深度
        - "basic": 基础提取（标题 + 正文），信用消耗 1/5个URL
        - "advanced": 高级提取（包括表格、嵌入内容），信用消耗 2/5个URL
        默认: "basic"

    输出格式: 默认返回 Markdown 格式

    使用示例:
        # 提取单个论文
        result = await tool.execute(
            urls=["https://arxiv.org/abs/1706.03762"],
            extract_depth="advanced"
        )

        # 批量提取多个网页
        result = await tool.execute(
            urls=["https://example.com/1", "https://example.com/2"]
        )
    """

    name = "tavily_extract"
    description = "从URL列表提取主要内容（Markdown格式），支持表格提取。"

    def __init__(self) -> None:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            self.client = None
        else:
            self.client = AsyncTavilyClient(api_key=api_key)

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行内容提取。

        返回格式:
            成功: {"error": False, "data": {"results": [...], "failed_results": [...]}}
            失败: {"error": True, "message": "错误信息"}
        """
        if self.client is None:
            return {"error": True, "message": "未配置 TAVILY_API_KEY"}

        urls = kwargs.get("urls")
        if not urls or not isinstance(urls, list):
            return {"error": True, "message": "缺少参数 urls（需为列表）"}

        if len(urls) > 20:
            return {"error": True, "message": "URLs 数量超限（最多 20 个）"}

        extract_params = {"urls": urls}

        if kwargs.get("extract_depth") is not None:
            extract_params["extract_depth"] = kwargs["extract_depth"]

        try:
            result = await self.client.extract(**extract_params)
            return {"error": False, "data": result}
        except Exception as e:
            return {"error": True, "message": f"Tavily Extract 调用失败: {e}"}

    def get_openai_definition(self) -> Dict[str, Any]:
        """返回OpenAI Function Calling定义，支持批量提取官网内容。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "调用 Tavily Extract 批量抓取网页正文，用于深入解析官方与知名站点。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "urls": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                            "maxItems": 20,
                            "description": "待提取的 URL 列表，最多 20 个。"
                        },
                        "extract_depth": {
                            "type": "string",
                            "enum": ["basic", "advanced"],
                            "description": "提取深度，advanced 会包含表格和嵌入内容。"
                        },
                        "include_raw_content": {
                            "type": "string",
                            "enum": ["markdown", "text"],
                            "description": "是否附加原始内容，格式可选 markdown 或 text。"
                        },
                        "include_images": {
                            "type": "boolean",
                            "description": "是否收集页面图片链接。"
                        },
                        "include_image_descriptions": {
                            "type": "boolean",
                            "description": "是否附加图片描述（需 include_images 为 true）。"
                        },
                        "include_favicon": {
                            "type": "boolean",
                            "description": "是否返回站点图标 URL。"
                        }
                    },
                    "required": ["urls"]
                }
            }
        }


class TavilyMapTool(BaseTool):
    """Tavily 网站结构映射工具（Beta）。

    适用场景：
    - 发现网站的所有页面链接
    - 获取文档网站的完整目录
    - 为后续爬取准备URL列表

    参数说明：
    - url (str, 必需): 起始URL（根页面）
        示例: "https://docs.tavily.com"
        示例: "https://python.langchain.com/docs"

    返回: URL 列表，可配合 TavilyExtractTool 批量提取内容

    使用示例:
        # 映射文档网站结构
        result = await tool.execute(url="https://docs.tavily.com")

        # 获取到的 URLs 可以传给 Extract 工具
        urls = result["data"]["results"]
        extract_result = await extract_tool.execute(urls=urls[:20])

    注意:
    - Beta 功能，可能不稳定
    - 默认只爬取1层深度，返回最多50个链接
    - 信用消耗: 1/10个成功页面
    """

    name = "tavily_map"
    description = "映射网站结构，返回所有页面URL列表。Beta功能。"

    def __init__(self) -> None:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            self.client = None
        else:
            self.client = AsyncTavilyClient(api_key=api_key)

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行网站映射。

        返回格式:
            成功: {"error": False, "data": {"base_url": "...", "results": [url1, url2, ...]}}
            失败: {"error": True, "message": "错误信息"}
        """
        if self.client is None:
            return {"error": True, "message": "未配置 TAVILY_API_KEY"}

        url = kwargs.get("url")
        if not url:
            return {"error": True, "message": "缺少参数 url"}

        try:
            result = await self.client.map(url=url)
            return {"error": False, "data": result}
        except Exception as e:
            return {"error": True, "message": f"Tavily Map 调用失败: {e}"}

    def get_openai_definition(self) -> Dict[str, Any]:
        """返回OpenAI Function Calling定义，便于获取站点结构。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "调用 Tavily Map 扫描站点结构，帮助定位官方文档页面。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "站点根地址，例如 https://docs.example.com。"
                        }
                    },
                    "required": ["url"]
                }
            }
        }


class TavilyCrawlTool(BaseTool):
    """Tavily 网站爬取工具（Beta）- Map + Extract 组合。

    适用场景：
    - 一步完成网站爬取 + 内容提取
    - 获取整个文档网站的内容

    参数说明：
    - url (str, 必需): 起始URL
        示例: "https://docs.tavily.com"

    - limit (int, 可选): 总页数上限，默认 50
        示例: 20

    返回: 直接返回提取后的内容（Markdown格式）

    使用示例:
        # 爬取文档网站前20页
        result = await tool.execute(
            url="https://docs.tavily.com",
            limit=20
        )

    注意:
    - Beta 功能
    - 信用消耗 = Map消耗 + Extract消耗
    - 默认返回 Markdown 格式，基础提取深度
    """

    name = "tavily_crawl"
    description = "爬取网站并提取内容（Map + Extract 组合）。Beta功能。"

    def __init__(self) -> None:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            self.client = None
        else:
            self.client = AsyncTavilyClient(api_key=api_key)

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行网站爬取。

        返回格式:
            成功: {"error": False, "data": {"base_url": "...", "results": [...]}}
            失败: {"error": True, "message": "错误信息"}
        """
        if self.client is None:
            return {"error": True, "message": "未配置 TAVILY_API_KEY"}

        url = kwargs.get("url")
        if not url:
            return {"error": True, "message": "缺少参数 url"}

        crawl_params = {"url": url}

        if kwargs.get("limit") is not None:
            crawl_params["limit"] = kwargs["limit"]

        try:
            result = await self.client.crawl(**crawl_params)
            return {"error": False, "data": result}
        except Exception as e:
            return {"error": True, "message": f"Tavily Crawl 调用失败: {e}"}

    def get_openai_definition(self) -> Dict[str, Any]:
        """返回OpenAI Function Calling定义，支持对子站点的深度爬取。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "调用 Tavily Crawl 对官方或知名站点执行深度爬取并提取内容。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "待爬取的站点或页面链接。"
                        },
                        "instructions": {
                            "type": "string",
                            "description": "爬取与提取指令，可指定关注的章节或信息类型。"
                        },
                        "max_depth": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "爬取深度，默认 1。"
                        },
                        "max_breadth": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "每层最大分支数量，默认 20。"
                        },
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "总抓取页面数上限。"
                        },
                        "select_paths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "允许的路径正则列表，可聚焦官方文档目录。"
                        },
                        "select_domains": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "允许的域名正则，确保仅抓取权威站点。"
                        },
                        "exclude_paths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "需排除的路径正则，避免无关内容。"
                        },
                        "exclude_domains": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "需排除的域名正则。"
                        },
                        "allow_external": {
                            "type": "boolean",
                            "description": "是否允许跟随外部链接，深度研究时建议 false。"
                        },
                        "include_images": {
                            "type": "boolean",
                            "description": "是否包含图片链接。"
                        },
                        "extract_depth": {
                            "type": "string",
                            "enum": ["basic", "advanced"],
                            "description": "内容提取深度，官方文档建议使用 advanced。"
                        },
                        "format": {
                            "type": "string",
                            "enum": ["markdown", "text"],
                            "description": "输出内容格式。"
                        },
                        "include_favicon": {
                            "type": "boolean",
                            "description": "是否返回站点图标 URL。"
                        }
                    },
                    "required": ["url"]
                }
            }
        }
