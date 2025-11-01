<div align="center">

<img src="https://github.com/MIKUSCAT/nanami-ai-assistant/blob/main/assets/nanami.png" width="300" alt="Nanami AI Assistant"/>

# 七海 AI 助手

**不只是对话，更是思考的伙伴**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-18-61dafb.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-latest-009688.svg)](https://fastapi.tiangolo.com/)

[演示视频](#) · [技术文档](#文档) · [快速开始](#快速开始) · [架构设计](#架构哲学)

</div>

---

## 💭 设计哲学

大多数 AI 助手只是简单的"问答机器"，但现实中的复杂任务需要：

- **分解思考** - 将大问题拆解为可执行的小步骤
- **深度探索** - 不满足于表面信息，主动深挖细节
- **记忆延续** - 记住你的偏好，成为真正了解你的伙伴
- **自主规划** - 像人类一样制定 TODO，而非机械执行

这就是七海的诞生理由。

---

## ✨ 核心创新

### 🏗️ 多 SubAgent 协作架构

**传统 AI**：单一 Agent 处理所有任务 → 上下文混乱、效率低下

**七海的方案**：将复杂任务分配给专业的 SubAgent，各司其职

```
                    ┌─────────────────────────────────┐
                    │   主 Agent (对话 + 任务编排)    │
                    │  "理解意图，分配任务，整合结果"  │
                    └────────────┬────────────────────┘
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
                ▼                ▼                ▼
    ┌───────────────────┐ ┌──────────────┐ ┌──────────────┐
    │ SearchSubAgent ✅ │ │ BrowserSub 🚧│ │ WindowsSub 🚧│
    │   深度搜索专家    │ │  浏览器控制  │ │ 桌面自动化   │
    ├───────────────────┤ ├──────────────┤ ├──────────────┤
    │• 学术检索         │ │• 网页交互    │ │• 应用启动    │
    │• 多源信息对比     │ │• 表单填写    │ │• UI 控制     │
    │• 内容深度提取     │ │• 自动化测试  │ │• 进程管理    │
    │• 网站结构分析     │ │• 视觉定位    │ │• 命令执行    │
    └───────────────────┘ └──────────────┘ └──────────────┘
```

**为什么需要多个 SubAgent？**

| 场景 | 传统方案 | 七海方案 | 优势 |
|------|---------|---------|------|
| **搜索论文** | 主Agent调用API→解析→总结 | 委托SearchSubAgent独立执行 | 上下文占用↓80% |
| **自动填表** | 主Agent逐步操作浏览器 | 委托BrowserSubAgent自主规划 | 多步骤流程更稳健 |
| **桌面操作** | 主Agent记忆所有UI状态 | 委托WindowsSubAgent隔离执行 | 工具内聚，易维护 |

---

## 🤖 SubAgent 详解

### 🔍 SearchSubAgent - 深度搜索专家 ✅

**状态**: 已完成并可用

**核心能力**:
- **深度检索** - Tavily API `max_results=10`, `search_depth="advanced"`
- **内容提取** - `tavily_extract` 提取完整网页内容
- **网站映射** - `tavily_map` 分析网站结构
- **深度爬取** - `tavily_crawl` 爬取整站信息

**使用场景**:
```
你: "请在 arXiv 和 Nature 上搜索 DeepSeek R1 的最新文章，并对比分析"
```

→ SearchSubAgent 自动规划：
1. 搜索 arXiv（深度模式，10条）
2. 搜索 Nature
3. 提取关键论文内容
4. 对比技术差异
5. 生成结构化报告

**技术亮点**:
- ⚡ 紧凑报告机制：仅返回摘要+关键发现+文件ID，主Agent上下文占用降低 **80%**
- 🎯 自主TODO规划：自动分解复杂搜索任务
- 🔧 工具内聚：拥有完整Tavily工具集

---

### 🌐 BrowserSubAgent - 浏览器操控专家 🚧

**状态**: 开发中 (预计 v0.2.0)

**设计理念**: 双路径架构
- **快速通道** - 视觉定位 + 坐标操作（简单任务，3步内）
- **稳健通道** - Playwright 选择器（复杂任务，多页面流程）

**核心能力**:
- **智能导航** - 自动处理页面跳转、弹窗、表单验证
- **视觉定位** - 截图 + AI 视觉分析 → 精确坐标点击
- **选择器操作** - `get_by_role` / `get_by_text` / `locator`（Playwright）
- **状态验证** - 动作前后自动验证，失败自动重试

**技术特点**:
- 🔍 **有头浏览器** - `headless=False`，可视化调试
- 🎯 **自适应策略** - 简单任务走视觉快速通道，复杂任务走选择器稳健通道
- 🔄 **自动等待** - Playwright actionability 自动检查可操作性

**使用场景**:
```
你: "帮我在京东上搜索 iPhone 15，筛选256G版本，查看前3个商品的价格和评价"
```

→ BrowserSubAgent 规划：
1. 打开京东官网
2. 搜索框输入 "iPhone 15"
3. 勾选 "256G" 筛选项
4. 循环提取前3个商品信息
5. 整理成表格返回

---

### 🖥️ WindowsSubAgent - 桌面自动化专家 🚧

**状态**: 开发中 (预计 v0.3.0)

**核心能力**:
- **应用管理** - 启动、切换、关闭应用程序
- **UI 控制** - 点击按钮、输入文本、选择菜单
- **进程管理** - 列举、监控、终止进程
- **命令执行** - PowerShell / CMD 命令调用
- **文件操作** - 读取、写入、移动文件

**技术特点**:
- 🎯 **视觉 + UI Automation** - 结合截图分析与系统API
- 🔄 **状态检查** - 操作前验证目标状态（如窗口是否已打开）
- 🛠️ **错误恢复** - 失败时自动调整计划并重试

**使用场景**:
```
你: "帮我打开 VS Code，新建一个 Python 文件，写入 Hello World 代码并保存到桌面"
```

→ WindowsSubAgent 规划：
1. 启动 VS Code
2. 等待主窗口加载
3. Ctrl+N 新建文件
4. 输入代码
5. Ctrl+S 保存到桌面
6. 验证文件已创建

---

## 🧠 三层记忆系统

| 记忆层级 | 作用 | 示例 |
|---------|------|------|
| **短期记忆** | 当前会话完整历史 | "刚才你问我的那个问题是..." |
| **中期记忆** | 自动压缩长上下文（阈值 92%） | 提取关键信息，删除冗余对话 |
| **长期记忆** | 持久化用户偏好到 Markdown | "你喜欢简洁的代码风格" |

---

## 🎨 产品特性

<table>
<tr>
<td width="50%">

### 💻 桌面应用（Frontend）

- 🖥️ **跨平台** - Windows/macOS/Linux
- 💬 **流式对话** - 实时响应，自然流畅
- 📝 **任务管理** - 内置 TODO，对话即规划
- 📎 **文件分析** - 拖拽上传，智能解析
- 🎨 **双主题** - 明亮/暗黑，护眼舒适
- 🗂️ **多会话** - 历史记录，自动标题

</td>
<td width="50%">

### ⚙️ 后端服务（Backend）

- 🏗️ **多SubAgent架构** - 3个专业SubAgent协作
- 🧠 **三层记忆** - 短期+中期+长期
- 🔍 **深度搜索** - Tavily 多工具集成
- 🤖 **七海人格** - 技术助手+义妹角色
- 📊 **紧凑报告** - 上下文优化 80%
- 🔧 **多模型支持** - OpenAI Compatible API

</td>
</tr>
</table>

---

## 🚀 快速开始

### 📋 前置要求

- **前端**: Node.js 16+ & npm
- **后端**: Python 3.9+
- **API Keys**:
  - OpenAI Compatible API（主模型 + 快速模型）
  - Tavily Search API

### 🔧 安装步骤

**1. 克隆仓库**
```bash
git clone https://github.com/MIKUSCAT/nanami-ai-assistant.git
cd nanami-ai-assistant
```

**2. 启动后端**
```bash
cd backend
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 API Keys

# 启动服务（默认端口 7878）
python main.py
```

**3. 启动前端**
```bash
cd ../frontend
npm install

# 开发模式
npm run electron:dev

# 构建应用
npm run electron:build
```

### 🎯 配置说明

编辑 `backend/.env`：

```bash
# 主模型（用于主Agent和SubAgent，支持多模态）
MAIN_PROVIDER='你的提供商'
MAIN_MODEL='模型名称'
MAIN_API_KEY='你的API密钥'
MAIN_BASE_URL='https://api.example.com/v1'

# 快速模型（用于记忆压缩和摘要）
QUICK_PROVIDER='DeepSeek'
QUICK_MODEL='deepseek-chat'
QUICK_API_KEY='你的API密钥'
QUICK_BASE_URL='https://api.deepseek.com/v1'

# Tavily 搜索 API
TAVILY_API_KEY='你的Tavily密钥'

# 服务器配置
HOST=0.0.0.0
PORT=7878
```

---

## 🛠️ 技术栈

<div align="center">

### 前端

![Electron](https://img.shields.io/badge/Electron-47848F?style=for-the-badge&logo=electron&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)

### 后端

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)
![Tavily](https://img.shields.io/badge/Tavily-FF6B6B?style=for-the-badge&logo=search&logoColor=white)

</div>

---

## 📁 项目结构

```
nanami-ai-assistant/
├── frontend/                    # Electron 桌面客户端
│   ├── src/
│   │   ├── components/          # React 组件
│   │   │   ├── TitleBar/        # 自定义标题栏
│   │   │   ├── Sidebar/         # 会话侧边栏
│   │   │   ├── MessageItem/     # 消息项
│   │   │   ├── ChatInput/       # 输入框
│   │   │   ├── TodoList/        # 任务列表
│   │   │   └── Settings/        # 设置面板
│   │   ├── services/            # API 服务层
│   │   ├── store/               # Zustand 状态管理
│   │   └── types/               # TypeScript 类型定义
│   ├── electron/                # Electron 主进程
│   └── package.json
│
└── backend/                     # FastAPI 后端服务
    ├── core/                    # 核心模块
    │   ├── agent_loop.py        # 主 Agent 循环
    │   ├── subagent.py          # SubAgent 基类
    │   ├── memory.py            # 记忆管理器
    │   ├── ltm.py               # 长期记忆
    │   ├── model_manager.py     # 模型管理器
    │   └── prompts.py           # 人格系统（七海设定）
    ├── tools/                   # 工具集
    │   ├── subagent_search.py   # ✅ 深度搜索 SubAgent
    │   ├── subagent_browser.py  # 🚧 浏览器操控 SubAgent
    │   ├── subagent_windows.py  # 🚧 Windows自动化 SubAgent
    │   ├── tavily_wrapper.py    # Tavily 搜索工具
    │   ├── todo_tools.py        # TODO 管理工具
    │   ├── file_tools.py        # 文件缓存工具
    │   └── vision_screenshot_tools.py  # 截图+视觉分析
    ├── services/                # 服务层
    │   ├── file_store.py        # 文件存储
    │   ├── todo_store.py        # TODO 存储
    │   └── report_store.py      # 报告存储
    ├── schemas/                 # 数据模型
    └── main.py                  # 应用入口
```

---

## 🎯 架构哲学

### 为什么需要 SubAgent？

**问题 1**：复杂任务时，主 Agent 需要多次调用工具，上下文快速膨胀
**解决**：将复杂任务委托给 SubAgent，它有独立的执行环境和工具集

**问题 2**：深度搜索/浏览器操作需要多轮规划，主 Agent 容易迷失方向
**解决**：SubAgent 内置 TODO 系统，能够自主分解任务、更新状态

**问题 3**：工具调用历史占用大量上下文
**解决**：SubAgent 仅返回紧凑报告，中间过程不传递给主 Agent

### SubAgent vs 直接工具调用

| 对比项 | 直接调用工具 | 使用 SubAgent |
|--------|-------------|--------------|
| **工具访问** | 主 Agent 逐个调用 | SubAgent 内部批量调用 |
| **任务规划** | 主 Agent 需要规划 | SubAgent 自主规划 TODO |
| **上下文占用** | 每次调用都占用 | 仅返回紧凑报告 |
| **错误恢复** | 主 Agent 处理 | SubAgent 自主重试 |
| **适用场景** | 简单单步操作 | 复杂多步流程 |

### 紧凑报告机制

SubAgent 仅返回紧凑报告，而非完整执行历史：

```json
{
  "summary": "找到15篇DeepSeek R1相关论文，核心创新...",  // 200字内摘要
  "key_findings": [                                      // 最多10条
    "671B参数MoE架构",
    "训练成本降低40%",
    "MMLU超越GPT-4"
  ],
  "artifacts": ["file_id_123"],    // 仅传文件ID，不传base64
  "todos_completed": 3,
  "todos_total": 3,
  "iterations": 5
}
```

**效果**：上下文占用降低 **80%**

---

## 🗓️ 开发路线图

### ✅ v0.1.0 - 当前版本

- [x] 基础 Electron 桌面应用
- [x] 流式对话 + 三层记忆系统
- [x] SearchSubAgent（深度搜索）
- [x] TODO 管理系统
- [x] 七海人格系统

### 🚧 v0.2.0 - 浏览器自动化（开发中）

- [ ] BrowserSubAgent 核心功能
- [ ] Playwright 有头浏览器集成
- [ ] 视觉定位 + 坐标操作
- [ ] 选择器策略（role/text/css）
- [ ] 多页面流程自动化

### 🔮 v0.3.0 - 桌面自动化（规划中）

- [ ] WindowsSubAgent 核心功能
- [ ] UI Automation 集成
- [ ] 应用启动与管理
- [ ] 进程监控与控制
- [ ] PowerShell 命令执行

### 🌟 v1.0.0 - 完整版本（未来）

- [ ] 3个SubAgent协同工作
- [ ] 跨SubAgent任务编排
- [ ] 性能优化与压力测试
- [ ] 完整文档与示例
- [ ] 社区贡献指南

---

## 📚 文档

- [前端开发文档](./frontend/README.md)
- [后端架构详解](./backend/README.md)
- [SubAgent 开发指南](#) (开发中)
- [API 接口文档](#) (开发中)
- [部署指南](#) (开发中)

---

## 🎨 使用场景

### 1️⃣ 学术研究助手（SearchSubAgent）

```
你: "请在arXiv和Nature上搜索DeepSeek R1的最新文章，并对比分析"
```

→ SearchSubAgent 自动规划：
1. 搜索 arXiv（深度模式，10条）
2. 搜索 Nature
3. 提取关键论文内容
4. 对比技术差异
5. 生成结构化报告

### 2️⃣ 电商价格监控（BrowserSubAgent - 开发中）

```
你: "每天上午10点检查京东iPhone 15 Pro的价格，如果低于7500元就通知我"
```

→ BrowserSubAgent 规划：
1. 定时打开京东商品页
2. 提取当前价格
3. 与目标价格对比
4. 价格达标时发送通知

### 3️⃣ 批量文档处理（WindowsSubAgent - 开发中）

```
你: "把桌面的20个Word文档都转成PDF，并按日期重命名"
```

→ WindowsSubAgent 规划：
1. 遍历桌面Word文件
2. 逐个打开并另存为PDF
3. 读取文件创建日期
4. 按格式重命名文件
5. 移动到指定文件夹

---

## 🤝 贡献

欢迎 Issue 和 Pull Request！

在提交 PR 前，请确保：
- 代码通过 lint 检查
- 遵循现有的代码风格
- 添加必要的注释和文档

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源。

---

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 高性能 Python Web 框架
- [Electron](https://www.electronjs.org/) - 跨平台桌面应用框架
- [Playwright](https://playwright.dev/) - 浏览器自动化工具
- [Tavily](https://tavily.com/) - AI 搜索 API
- [OpenAI](https://openai.com/) - AI 模型提供商

---

## 💡 灵感来源

这个项目的灵感来自于对"真正有用的 AI 助手"的思考：

> 当我需要研究一个技术问题时，我不想要一个只会给我3条搜索结果的助手。我需要一个能够：
> - 在多个学术数据库深度检索
> - 提取完整论文内容并总结
> - 对比不同来源的信息
> - 生成结构化的报告
>
> 这就是 **SearchSubAgent** 的诞生理由。

> 当我需要自动化浏览器操作时，我不想手动点击几十次。我需要一个能够：
> - 理解我的意图
> - 自主规划执行步骤
> - 处理复杂的多页面流程
> - 自动处理错误和重试
>
> 这就是 **BrowserSubAgent** 的设计初衷。

> 当我需要批量处理桌面任务时，我不想写复杂的脚本。我需要一个能够：
> - 用自然语言描述任务
> - 自动调用系统API
> - 可视化验证执行结果
> - 智能处理异常情况
>
> 这就是 **WindowsSubAgent** 的愿景。

**七海，不只是一个AI助手，更是你的思考伙伴。**

---

<div align="center">

**💙 Built with passion by MIKUSCAT**

如果这个项目对你有帮助，请给个 ⭐ Star 支持一下！

[⬆ 回到顶部](#七海-ai-助手)

</div>
