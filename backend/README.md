<div align="center">

# 七海 AI 助手 - 后端服务 🤖

**基于 SubAgent 架构的智能 AI Agent 系统**

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-latest-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](../LICENSE)

</div>

---

## 💡 核心创新

### 🏗️ 多 SubAgent 协作架构

将复杂任务分配给专业的 SubAgent，各司其职，主 Agent 仅负责任务编排和结果整合。

```
              主 Agent
                 ↓
    ┌────────────┼────────────┐
    ↓            ↓            ↓
SearchAgent  BrowserAgent  WindowsAgent
  (搜索)       (浏览器)     (桌面)
```

**关键优势**：
- ⚡ **上下文优化** - SubAgent 仅返回紧凑报告，主 Agent 上下文占用降低 **80%**
- 🎯 **职责分离** - 主 Agent 专注对话，SubAgent 专注执行
- 🧠 **自主规划** - SubAgent 内置 TODO 系统，自动分解复杂任务
- 🔧 **工具内聚** - 每个 SubAgent 拥有完整的专业工具集

### 🧠 三层记忆系统

| 记忆层级 | 作用 | 触发条件 |
|---------|------|---------|
| **短期记忆** | 当前会话完整历史 | 实时存储 |
| **中期记忆** | 自动压缩长上下文 | Token 使用率 > 92% |
| **长期记忆** | 持久化用户偏好 | 用户主动保存 |

### 🤖 七海人格系统

- 完整的有栖原七海（Arihara Nanami）人格设定
- 技术助手 + 义妹角色融合
- 自然流畅的对话风格
- 高精度时间系统（精确到秒）

---

## 🤖 SubAgent 详解

### ✅ SearchSubAgent - 深度搜索专家

**状态**: 已完成并可用

**核心能力**:
- 🔍 深度检索 - `max_results=10`, `search_depth="advanced"`
- 📄 内容提取 - `tavily_extract` 完整网页内容
- 🗺️ 网站映射 - `tavily_map` 网站结构分析
- 🕷️ 深度爬取 - `tavily_crawl` 整站信息收集

**技术亮点**:
- 紧凑报告机制（仅返回摘要+关键发现+文件ID）
- 自主 TODO 规划（自动分解复杂搜索任务）
- 工具内聚（完整 Tavily 工具集）

---

### 🚧 BrowserSubAgent - 浏览器操控专家

**状态**: 开发中 (v0.2.0)

**设计理念**: 双路径架构
- **快速通道** - 视觉定位 + 坐标操作（简单任务）
- **稳健通道** - Playwright 选择器（复杂流程）

**核心能力**:
- 🌐 智能导航 - 页面跳转、弹窗处理、表单验证
- 👁️ 视觉定位 - 截图 + AI 视觉分析 → 精确坐标
- 🎯 选择器操作 - `get_by_role` / `get_by_text` / `locator`
- ✅ 状态验证 - 动作前后自动验证，失败重试

---

### 🚧 WindowsSubAgent - 桌面自动化专家

**状态**: 开发中 (v0.3.0)

**核心能力**:
- 🚀 应用管理 - 启动、切换、关闭应用
- 🖱️ UI 控制 - 点击、输入、选择菜单
- 📊 进程管理 - 列举、监控、终止进程
- ⚡ 命令执行 - PowerShell / CMD 调用
- 📁 文件操作 - 读取、写入、移动文件

---

## 🚀 快速开始

### 📋 系统要求

- **Python**: 3.9+
- **操作系统**: Windows / macOS / Linux
- **API 密钥**:
  - OpenAI Compatible API（主模型 + 压缩模型）
  - Tavily Search API

### 🔧 安装步骤

**1. 安装依赖**

```bash
pip install -r requirements.txt
```

**2. 配置环境变量**

复制 `.env.example` 为 `.env`：

```bash
cp .env.example .env
```

然后编辑 `.env` 文件，填入你的 API 密钥。

**3. 启动服务**

```bash
# 方式1：直接运行
python main.py

# 方式2：使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 7878 --reload
```

服务启动后访问：`http://localhost:7878/health`

---

## ⚙️ 配置说明

### 📝 环境变量详解

编辑 `backend/.env`，以下是完整的配置说明：

#### 1️⃣ 主模型配置（用于主 Agent 对话）

```bash
# 主模型配置
MAIN_PROVIDER='OpenAI'                # 提供商名称（仅用于日志）
MAIN_MODEL='gpt-4'                    # 模型名称
MAIN_API_KEY='sk-your-api-key'       # API 密钥
MAIN_BASE_URL='https://api.openai.com/v1'  # API 端点
MAIN_CONTEXT_LENGTH='128000'         # 上下文长度
```

#### 2️⃣ 压缩模型配置（用于上下文压缩，节省成本）

```bash
# 压缩模型（建议使用便宜的模型，如 DeepSeek）
COMPACT_PROVIDER='DeepSeek'
COMPACT_MODEL='deepseek-chat'
COMPACT_API_KEY='sk-your-deepseek-key'
COMPACT_BASE_URL='https://api.deepseek.com/v1'
COMPACT_CONTEXT_LENGTH='128000'
```

#### 3️⃣ 快速模型配置（用于简单任务）

```bash
# 快速模型（用于简单任务，可与主模型相同）
QUICK_PROVIDER='OpenAI'
QUICK_MODEL='gpt-3.5-turbo'
QUICK_API_KEY='sk-your-api-key'
QUICK_BASE_URL='https://api.openai.com/v1'
QUICK_CONTEXT_LENGTH='16000'
```

#### 4️⃣ SubAgent 独立配置

每个 SubAgent 可以使用不同的模型，根据任务特点选择：

```bash
# SearchSubAgent - 深度搜索（推荐强模型）
SEARCH_AGENT_PROVIDER='OpenAI'
SEARCH_AGENT_MODEL='gpt-4'
SEARCH_AGENT_API_KEY='sk-your-api-key'
SEARCH_AGENT_BASE_URL='https://api.openai.com/v1'
SEARCH_AGENT_CONTEXT_LENGTH='128000'

# BrowserSubAgent - 浏览器操控（推荐视觉模型）
BROWSER_AGENT_PROVIDER='OpenAI'
BROWSER_AGENT_MODEL='gpt-4-vision-preview'
BROWSER_AGENT_API_KEY='sk-your-api-key'
BROWSER_AGENT_BASE_URL='https://api.openai.com/v1'
BROWSER_AGENT_CONTEXT_LENGTH='128000'

# WindowsSubAgent - 桌面自动化
WINDOWS_AGENT_PROVIDER='DeepSeek'
WINDOWS_AGENT_MODEL='deepseek-chat'
WINDOWS_AGENT_API_KEY='sk-your-deepseek-key'
WINDOWS_AGENT_BASE_URL='https://api.deepseek.com/v1'
WINDOWS_AGENT_CONTEXT_LENGTH='128000'
```

#### 5️⃣ Tavily 搜索 API

```bash
# Tavily 搜索引擎（深度搜索必需）
TAVILY_API_KEY='tvly-your-tavily-key'
```

获取 Tavily API Key：访问 [https://tavily.com/](https://tavily.com/)

#### 6️⃣ 服务器与性能配置

```bash
# 服务器设置
HOST=0.0.0.0
PORT=7878

# 工作目录
WORKSPACE_ROOT='./workspace'
ALLOW_FILE_READ=true

# 上下文压缩阈值（0~1 之间）
AUTO_COMPACT_RATIO=0.92

# 长期记忆配置
LTM_MD_ENABLED=1
LTM_MD_PATH='data/ltm.md'

# 工具结果截断（字节）
TOOL_RESULT_MAX_SIZE=10240
```

#### 7️⃣ API 速率限制配置（避免 502 错误）

```bash
# LLM API 最小请求间隔（秒）
# 如果你的 API 限制 30 rpm，则设置为 60/30=2 秒
LLM_MIN_INTERVAL=2.5

# 工具执行超时（秒）
# SearchSubAgent 可能需要 10-15 轮迭代
TOOL_EXECUTION_TIMEOUT=600

# SubAgent 迭代延迟（秒）
SUBAGENT_ITERATION_DELAY=0
```

---

## 💰 成本优化建议

### 多模型策略

通过为不同任务配置不同模型，显著降低成本：

| 任务类型 | 推荐模型 | 原因 |
|---------|---------|------|
| **主对话** | GPT-4 / Claude 3.5 | 需要高质量对话 |
| **上下文压缩** | DeepSeek / GPT-3.5 | 简单摘要任务，用便宜模型 |
| **搜索任务** | GPT-4 | 需要深度理解和规划 |
| **浏览器操作** | GPT-4-Vision | 需要视觉理解 |
| **桌面自动化** | DeepSeek | 简单指令执行，便宜即可 |

**示例配置**（低成本方案）：
```bash
MAIN_MODEL='gpt-4-turbo'          # 主对话用 GPT-4
COMPACT_MODEL='deepseek-chat'     # 压缩用 DeepSeek（便宜）
QUICK_MODEL='gpt-3.5-turbo'       # 快速任务用 3.5
SEARCH_AGENT_MODEL='gpt-4'        # 搜索用 GPT-4
BROWSER_AGENT_MODEL='deepseek'    # 浏览器用 DeepSeek
WINDOWS_AGENT_MODEL='deepseek'    # Windows 用 DeepSeek
```

**成本对比**：
- 全 GPT-4：~$0.03/1K tokens × 100K = **$3.00**
- 混合方案：~$0.01/1K tokens × 100K = **$1.00** （节省 67%）

---

## 📡 API 接口

### 核心端点

```http
GET  /health                # 健康检查
POST /chat                  # 流式对话（支持文件上传）
POST /v1/chat/completions   # OpenAI 兼容接口
POST /upload                # 文件上传
GET  /todos                 # 获取任务列表
POST /todos                 # 创建任务
PUT  /todos/{id}            # 更新任务
DELETE /todos/{id}          # 删除任务
POST /preferences/save      # 保存用户偏好到长期记忆
```

### 流式对话示例

**请求**：
```bash
curl -X POST http://localhost:7878/chat \
  -F "input=请在arXiv上搜索DeepSeek R1的论文并总结核心创新" \
  -F "session_id=default"
```

**响应**（Server-Sent Events）：
```
[meta] {"session_id": "default", "timestamp": 1234567890}
[🔧 正在调用1个工具...]
[✓ search_subagent]: {"summary": "找到15篇相关论文...", "key_findings": [...]}
DeepSeek R1 的核心创新包括：
1. 671B 参数 MoE 架构...
```

---

## 📁 项目结构

```
backend/
├── main.py                          # FastAPI 应用入口
├── requirements.txt                 # Python 依赖
├── .env.example                     # 环境变量模板
│
├── core/                            # 核心模块
│   ├── agent_loop.py               # 主 Agent 循环
│   ├── subagent.py                 # SubAgent 基类
│   ├── memory.py                   # 记忆管理器
│   ├── ltm.py                      # 长期记忆
│   ├── model_manager.py            # 模型管理器
│   └── prompts.py                  # 七海人格系统
│
├── tools/                           # 工具集
│   ├── subagent_search.py          # ✅ SearchSubAgent
│   ├── subagent_browser.py         # 🚧 BrowserSubAgent
│   ├── subagent_windows.py         # 🚧 WindowsSubAgent
│   ├── tavily_wrapper.py           # Tavily 搜索工具
│   ├── todo_tools.py               # TODO 管理
│   ├── file_tools.py               # 文件缓存
│   └── vision_screenshot_tools.py  # 截图+视觉分析
│
├── services/                        # 服务层
│   ├── file_store.py               # 文件存储
│   ├── todo_store.py               # TODO 存储
│   └── report_store.py             # 报告存储
│
└── schemas/                         # 数据模型
    ├── openai.py                   # OpenAI 格式
    ├── todo.py                     # TODO 模型
    └── preferences.py              # 偏好设置
```

---

## 🎯 使用场景

### 场景 1：学术研究助手

```python
"请在 arXiv 和 Nature 上搜索 Transformer 架构的最新进展，并对比分析"
```

**执行流程**：
1. 主 Agent 识别为深度搜索任务
2. 调用 SearchSubAgent
3. SearchSubAgent 创建 TODO：
   - 搜索 arXiv（深度模式）
   - 搜索 Nature
   - 提取论文内容
   - 对比分析
   - 生成结构化报告
4. 返回紧凑报告给主 Agent
5. 主 Agent 整合并呈现给用户

### 场景 2：电商价格监控（开发中）

```python
"每天上午10点检查京东 iPhone 15 的价格，低于7500元就通知我"
```

**执行流程**：
1. 主 Agent 识别为浏览器自动化任务
2. 调用 BrowserSubAgent
3. BrowserSubAgent 执行：
   - 打开京东商品页
   - 提取价格信息
   - 与目标价格对比
   - 触发通知（如果满足条件）

### 场景 3：批量文档处理（开发中）

```python
"把桌面的 20 个 Word 文档都转成 PDF"
```

**执行流程**：
1. 主 Agent 识别为桌面自动化任务
2. 调用 WindowsSubAgent
3. WindowsSubAgent 执行：
   - 遍历桌面 .docx 文件
   - 逐个打开并另存为 PDF
   - 关闭 Word
   - 生成执行报告

---

## 🔧 开发指南

### 创建自定义 SubAgent

```python
from core.subagent import SubAgent
from tools.base import BaseTool

class MyCustomSubAgent(SubAgent):
    def __init__(self, max_iterations: int = 10):
        super().__init__(
            name="MyCustomSubAgent",
            description="你的 SubAgent 描述",
            system_prompt="你是一个专门的 SubAgent...",
            max_iterations=max_iterations,
            model_pointer="custom_agent"  # 使用独立模型配置
        )

    def _register_tools(self):
        """注册 SubAgent 专用工具"""
        self.tools = [
            MyCustomTool(),
            # ... 更多工具
        ]
```

在 `.env` 中添加模型配置：

```bash
CUSTOM_AGENT_PROVIDER='OpenAI'
CUSTOM_AGENT_MODEL='gpt-4'
CUSTOM_AGENT_API_KEY='sk-xxx'
CUSTOM_AGENT_BASE_URL='https://api.openai.com/v1'
```

---

## 🐛 常见问题

### Q1: 502 Bad Gateway 错误

**原因**: API 调用频率超过限制

**解决方案**：
```bash
# 增加请求间隔
LLM_MIN_INTERVAL=3.0

# 增加 SubAgent 迭代延迟
SUBAGENT_ITERATION_DELAY=1.5
```

### Q2: 上下文长度超限

**原因**: 对话历史过长

**解决方案**：
```bash
# 降低压缩阈值（更早触发压缩）
AUTO_COMPACT_RATIO=0.85

# 减少工具结果大小
TOOL_RESULT_MAX_SIZE=5120
```

### Q3: SearchSubAgent 超时

**原因**: 搜索任务复杂，需要较长时间

**解决方案**：
```bash
# 增加工具执行超时
TOOL_EXECUTION_TIMEOUT=900  # 15分钟
```

---

## 📄 许可证

MIT License

---

<div align="center">

**💙 Built with FastAPI + Python**

[返回主项目](../) | [前端文档](../frontend/README.md)

</div>
