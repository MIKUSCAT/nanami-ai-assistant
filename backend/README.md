# 七海-后端 🤖

> 基于 SubAgent 架构的 AI Agent 系统 | FastAPI + Python

[![Status](https://img.shields.io/badge/status-active-success)]()
[![Python](https://img.shields.io/badge/python-3.9+-blue)]()
[![FastAPI](https://img.shields.io/badge/fastapi-latest-green)]()

## ✨ 核心创新

### 🏗️ SubAgent 分层架构

**核心思想**：主 Agent 负责任务编排，SearchSubAgent 负责深度搜索执行

```
     主Agent（任务理解 + 结果整合）
            │
            ▼
    SearchSubAgent（深度搜索专家）
     ├─ TODO自主规划
     ├─ 多源信息检索
     ├─ 内容深度提取
     └─ 紧凑报告生成
```

**关键优势**：
- ✅ **上下文优化** - SubAgent 仅返回紧凑报告（摘要+关键发现+文件ID），主 Agent 上下文占用降低 80%
- ✅ **职责分离** - 主 Agent 专注对话和任务分配，SubAgent 专注执行和规划
- ✅ **自主规划** - SubAgent 内置 TODO 系统，能够自主分解复杂搜索任务
- ✅ **工具内聚** - SearchSubAgent 拥有完整 Tavily 工具集（search/extract/map/crawl），主 Agent 仅保留轻度搜索

### 🤖 七海人格系统

- 完整的有栖原七海（Arihara Nanami）人格设定
- 自然流畅的对话风格，技术助手+义妹角色融合
- 高精度时间系统（精确到秒）

### 🧠 三层记忆系统

- **短期记忆** - 当前会话完整历史
- **中期记忆** - 自动压缩长上下文（阈值 92% 可配）
- **长期记忆** - 持久化用户偏好到 Markdown

### 🔍 深度搜索能力（SearchSubAgent）

相比主 Agent 的轻度搜索（3条结果，basic深度），SearchSubAgent 提供：
- **深度检索** - max_results=10，search_depth="advanced"
- **内容提取** - 使用 tavily_extract 提取 URL 完整内容
- **网站映射** - 使用 tavily_map 分析网站结构
- **深度爬取** - 使用 tavily_crawl 爬取整站信息

## 🛠️ 技术栈

| 类别 | 技术 |
|-----|------|
| **后端框架** | FastAPI + Uvicorn |
| **AI 模型** | OpenAI Compatible API（多模型配置） |
| **搜索引擎** | Tavily Search API |
| **记忆管理** | 三层记忆 + 自动压缩 + Markdown 持久化 |
| **数据存储** | JSON + File Store |

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，配置以下关键参数：

```bash
# 主模型（用于主Agent和SubAgent，支持多模态）
MAIN_PROVIDER='公益站'
MAIN_MODEL='openai.gpt-5-chat'
MAIN_API_KEY='your_api_key_here'
MAIN_BASE_URL='https://aigate.binklac.com/v1'

# 快速模型（用于记忆压缩和摘要）
QUICK_PROVIDER='DeepSeek'
QUICK_MODEL='deepseek-v3.1:671b'
QUICK_API_KEY='your_api_key_here'
QUICK_BASE_URL='https://fanyi.963312.xyz/v1'

# Tavily 搜索 API
TAVILY_API_KEY='your_tavily_key_here'

# 服务器配置
HOST=0.0.0.0
PORT=7878
```

### 3. 启动服务

```bash
# 方式1：使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 7878 --reload

# 方式2：直接运行
python main.py
```

服务启动后访问：`http://localhost:7878/health`

## 📡 API 接口

### 核心端点

```http
GET  /health              # 健康检查
POST /chat                # 流式对话（支持文件上传）
POST /v1/chat/completions # OpenAI 兼容接口
POST /upload              # 文件上传
GET  /todos               # 获取任务列表
POST /todos               # 创建任务
```

### 流式对话示例

```bash
curl -X POST http://localhost:7878/chat \
  -F "input=请在arXiv上搜索DeepSeek R1的论文并总结核心创新"
```

**流式响应格式**：
```
[meta] {"session_id": "...", "timestamp": ...}
[🔧 正在调用1个工具...]
[✓ search_subagent]: {"summary": "找到15篇相关论文...", ...}
文本内容...
```

## 🎯 SubAgent 架构详解

### SearchSubAgent 工作流程

```
用户请求："搜索arXiv上的DeepSeek R1论文"
   ↓
主 Agent 分析任务 → 决定调用 search_subagent
   ↓
┌─────── SearchSubAgent 执行 ───────┐
│ 1. 创建 TODO LIST                 │
│    - 搜索arXiv                     │
│    - 提取论文内容                  │
│    - 总结核心创新                  │
│                                    │
│ 2. 使用 Tavily 工具执行            │
│    - tavily_search (深度，10条)   │
│    - tavily_extract (提取内容)    │
│                                    │
│ 3. 更新 TODO 状态                  │
│                                    │
│ 4. 生成紧凑报告                    │
│    {                               │
│      "summary": "执行摘要",        │
│      "key_findings": ["发现1"...], │
│      "artifacts": ["file_id"],     │
│      "todos_completed": 3,         │
│      "todos_total": 3              │
│    }                               │
└────────────────────────────────────┘
   ↓
主 Agent 接收报告 → 整合呈现给用户
```

### 紧凑报告机制

**问题**：SubAgent 如果返回完整执行历史，会导致主 Agent 上下文爆炸

**解决方案**：SubAgent 仅返回紧凑报告

```python
{
  "error": False,
  "summary": "找到15篇DeepSeek R1相关论文，核心创新...",  # 200字内摘要
  "key_findings": [                                      # 最多10条关键发现
    "671B参数MoE架构",
    "训练成本降低40%",
    "MMLU超越GPT-4"
  ],
  "artifacts": ["file_id_123"],    # 仅传文件ID，不传base64
  "todos_completed": 3,
  "todos_total": 3,
  "iterations": 5,
  "subagent": "SearchSubAgent"
}
```

**效果**：
- ❌ 不传递：SubAgent 的完整 memory、工具调用历史、中间结果
- ✅ 仅传递：摘要、关键发现、文件 ID
- 📊 结果：上下文占用降低 **80%**

## 📁 项目结构

```
七海-后端/
├── main.py                          # FastAPI 应用入口
├── requirements.txt                 # 依赖列表
├── .env                             # 环境变量配置
│
├── core/                            # 核心模块
│   ├── agent_loop.py               # 主 Agent 循环（任务分配+报告整合）
│   ├── subagent.py                 # SubAgent 基类（TODO+工具执行）
│   ├── memory.py                   # 记忆管理器（三层记忆）
│   ├── ltm.py                      # 长期记忆（Markdown 持久化）
│   ├── model_manager.py            # 模型管理器
│   └── prompts.py                  # 人格系统（七海设定）
│
├── tools/                           # 工具集
│   ├── manager.py                  # 工具管理器
│   ├── subagent_search.py          # 深度搜索 SubAgent ⭐
│   ├── tavily_wrapper.py           # Tavily 搜索工具
│   ├── todo_tools.py               # TODO 管理工具
│   ├── file_tools.py               # 文件缓存工具
│   └── vision_screenshot_tools.py  # 截图工具
│
├── services/                        # 服务层
│   ├── file_store.py               # 文件存储
│   ├── todo_store.py               # TODO 存储
│   └── report_store.py             # 报告存储
│
├── schemas/                         # 数据模型
│   ├── openai.py                   # OpenAI 格式
│   ├── todo.py                     # TODO 模型
│   └── preferences.py              # 偏好设置
│
└── data/                            # 数据目录
    ├── uploads/                    # 上传文件
    └── ltm.md                      # 长期记忆
```

## 🔧 主要工具

### 主 Agent 工具集

| 工具名 | 功能 | 说明 |
|--------|------|------|
| `tavily_search` | 轻度搜索 | 3条结果，快速了解 |
| `screenshot` | 快速截图 | 全屏/窗口/区域截图 |
| `screenshot_and_analyze` | 截图+分析 | 一步完成截图和内容分析 |
| `search_subagent` | 深度搜索 SubAgent ⭐ | 学术/技术深度检索 |
| TODO 管理 (5个) | 任务管理 | 创建、更新、删除、查看、排序 |
| 文件缓存 (4个) | 文件操作 | 保存、列表、统计、清理 |

### SearchSubAgent 工具集

| 工具名 | 功能 |
|--------|------|
| `tavily_search` | 深度搜索（max_results=10, depth="advanced"） |
| `tavily_extract` | URL 内容提取 |
| `tavily_map` | 网站结构映射 |
| `tavily_crawl` | 网站深度爬取 |

## 🎯 使用场景

### 1. 学术研究助手

```python
"请在arXiv和Nature上搜索DeepSeek R1的最新文章，并对比分析"
```

→ SearchSubAgent 自动规划：
1. 搜索 arXiv（深度模式，10条）
2. 搜索 Nature
3. 提取关键论文内容
4. 对比技术差异
5. 生成结构化报告

### 2. 技术文档收集

```python
"收集FastAPI官方文档中关于异步处理的所有章节"
```

→ SearchSubAgent 执行：
1. 使用 tavily_map 映射官网结构
2. 使用 tavily_crawl 爬取相关页面
3. 使用 tavily_extract 提取具体内容
4. 整理成紧凑报告

### 3. 多源信息对比

```python
"对比GitHub、Reddit、HackerNews上关于Claude Code的讨论"
```

→ SearchSubAgent 规划：
1. 分别搜索三个平台
2. 提取关键讨论点
3. 分析情绪倾向
4. 生成对比表格

## ⚙️ 配置说明

### 关键环境变量

```bash
# 主 Agent 配置
MAIN_MAX_ITERATIONS=15               # 主 Agent 最大迭代次数
AUTO_COMPACT_RATIO=0.92              # 上下文压缩阈值

# SubAgent 配置
SUBAGENT_MAX_ITERATIONS=10           # SubAgent 最大迭代次数
SEARCH_AGENT_MODEL='openai.gpt-5-chat'  # SearchSubAgent 专用模型

# 长期记忆配置
LTM_MD_ENABLED=1                     # 是否启用长期记忆
LTM_MD_PATH=data/ltm.md             # 长期记忆存储路径

# 上下文管理
TOOL_RESULT_MAX_SIZE=10240           # 工具结果最大大小（10KB）
```

## 🔄 SubAgent 设计理念

### 为什么需要 SubAgent？

**问题 1**：搜索任务复杂时，主 Agent 需要多次调用工具，上下文快速膨胀

**解决**：将复杂搜索任务委托给 SearchSubAgent，它有独立的执行环境和工具集

**问题 2**：深度搜索需要多轮规划和调整，主 Agent 容易迷失方向

**解决**：SubAgent 内置 TODO 系统，能够自主分解任务、更新状态

**问题 3**：工具调用历史占用大量上下文

**解决**：SubAgent 仅返回紧凑报告，中间过程不传递给主 Agent

### SubAgent vs 直接工具调用

| 对比项 | 直接调用工具 | 使用 SubAgent |
|--------|-------------|--------------|
| 工具访问 | 主 Agent 逐个调用 | SubAgent 内部批量调用 |
| 任务规划 | 主 Agent 需要规划 | SubAgent 自主规划 TODO |
| 上下文占用 | 每次调用都占用 | 仅返回紧凑报告 |
| 错误恢复 | 主 Agent 处理 | SubAgent 自主重试 |
| 适用场景 | 简单单步操作 | 复杂多步流程 |

## 📝 技术亮点总结

1. **SubAgent 分层架构** - 职责分离，主 Agent 轻量化
2. **紧凑报告机制** - 上下文优化，降低 80% 占用
3. **TODO 自主规划** - SubAgent 能够自主分解任务
4. **多模型配置** - 主 Agent、SubAgent、压缩模型可独立配置
5. **三层记忆系统** - 短期+中期+长期，完整的记忆管理
6. **七海人格系统** - 自然流畅的对话体验

## 📄 许可证

MIT License

---

💙 Built with FastAPI + Python | 七海团队
