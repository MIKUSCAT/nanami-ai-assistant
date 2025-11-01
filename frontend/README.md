# 七海 - AI 助手桌面应用 🌊

> 优雅、轻量的 AI 聊天桌面客户端，基于 Electron + React 构建

## ✨ 核心特性

- **🖥️ 跨平台桌面应用** - Windows/macOS/Linux 原生体验
- **💬 流式实时对话** - 自然流畅的 AI 交互体验
- **📝 智能任务管理** - 内置 TODO 列表，对话与任务无缝协作
- **📎 文件上传分析** - 支持拖拽或选择文件进行分析
- **🎨 双主题切换** - 明亮/暗黑主题，护眼舒适
- **🗂️ 多会话管理** - 会话历史与自动标题生成
- **💾 偏好记忆** - 一键保存对话偏好到长期记忆

## 🛠️ 技术栈

| 类别 | 技术 |
|-----|------|
| **核心框架** | Electron + React 18 + TypeScript |
| **构建工具** | Vite |
| **状态管理** | Zustand |
| **UI样式** | Tailwind CSS |
| **Markdown** | markdown-it + highlight.js |
| **图标** | Lucide React |

## 🚀 快速开始

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run electron:dev
```

### 构建应用

```bash
npm run electron:build
```

构建产物位于 `release/` 目录

## 📁 项目结构

```
src/
├── components/        # UI 组件
│   ├── TitleBar/     # 自定义标题栏
│   ├── Sidebar/      # 会话侧边栏
│   ├── MessageItem/  # 消息项
│   ├── ChatInput/    # 输入框
│   ├── TodoList/     # 任务列表
│   └── Settings/     # 设置面板
├── services/         # API 服务
│   └── api.ts       # 后端通信
├── store/           # Zustand 状态
│   └── chat.ts      # 聊天状态管理
├── types/           # TypeScript 类型
└── App.tsx          # 主应用组件

electron/
├── main.ts          # Electron 主进程
└── preload.ts       # 预加载脚本
```

## ⚙️ 配置

### 后端 API 地址

在 `src/config.ts` 中配置：

```typescript
export const API_BASE_URL = 'http://localhost:7878'
```

### 启动后端服务

```bash
cd ../七海-后端
py main.py
```

## 🎨 设计理念

**简约而不简单** - 参考 Cherry Studio 设计风格

- 清晰的视觉层次与信息结构
- 流畅的交互动画与过渡效果
- 优雅的配色方案（深色 #1F2428 / 浅色 #FCF9F5）
- 精致的细节处理与用户体验

## 📄 许可证

MIT License

---

💙 Built with React + Electron | 七海团队
