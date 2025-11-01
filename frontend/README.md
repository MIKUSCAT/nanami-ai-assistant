<div align="center">

# 七海 AI 助手 - 桌面应用 🌊

**优雅、轻量的 AI 聊天桌面客户端**

[![Electron](https://img.shields.io/badge/Electron-47848F?logo=electron&logoColor=white)](https://www.electronjs.org/)
[![React](https://img.shields.io/badge/React-18-61dafb?logo=react)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](../LICENSE)

</div>

---

## ✨ 核心特性

<table>
<tr>
<td width="50%">

### 💬 对话体验
- **流式响应** - 实时显示 AI 回复
- **多会话管理** - 无限对话历史
- **自动标题** - 智能生成会话标题
- **Markdown 渲染** - 支持代码高亮

</td>
<td width="50%">

### 🎨 视觉设计
- **双主题** - 明亮/暗黑自由切换
- **自定义标题栏** - 原生窗口控制
- **流畅动画** - 优雅的过渡效果
- **响应式布局** - 适配各种屏幕

</td>
</tr>
<tr>
<td width="50%">

### 📝 任务管理
- **内置 TODO** - 对话即规划
- **状态追踪** - 实时更新任务进度
- **快速操作** - 一键完成/删除
- **持久化存储** - 任务不丢失

</td>
<td width="50%">

### 📎 文件处理
- **拖拽上传** - 拖入即分析
- **多格式支持** - 文本/图片/文档
- **智能解析** - AI 自动理解内容
- **文件预览** - 查看上传历史

</td>
</tr>
</table>

---

## 🛠️ 技术栈

<div align="center">

![Electron](https://img.shields.io/badge/Electron-47848F?style=for-the-badge&logo=electron&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![Zustand](https://img.shields.io/badge/Zustand-433E38?style=for-the-badge&logo=react&logoColor=white)

</div>

| 类别 | 技术 | 用途 |
|-----|------|------|
| **桌面框架** | Electron | 跨平台桌面应用 |
| **UI 框架** | React 18 | 用户界面 |
| **类型系统** | TypeScript | 类型安全 |
| **构建工具** | Vite | 快速开发与构建 |
| **状态管理** | Zustand | 全局状态 |
| **样式方案** | Tailwind CSS | 原子化 CSS |
| **Markdown** | markdown-it | Markdown 渲染 |
| **代码高亮** | highlight.js | 语法高亮 |
| **图标库** | Lucide React | 图标组件 |

---

## 🚀 快速开始

### 📋 前置要求

- **Node.js**: 16.x 或更高版本
- **npm**: 7.x 或更高版本
- **后端服务**: 确保后端服务已启动（默认 `http://localhost:7878`）

### 🔧 开发步骤

**1. 安装依赖**

```bash
npm install
```

**2. 启动开发模式**

```bash
npm run electron:dev
```

这会同时启动：
- Vite 开发服务器（React 热更新）
- Electron 主进程（桌面窗口）

**3. 构建生产版本**

```bash
npm run electron:build
```

构建产物位于 `release/` 目录。

---

## 📦 打包成 .exe

### Windows 平台

项目已配置 `electron-builder`，直接运行：

```bash
npm run electron:build
```

**输出位置**：
- `release/` - 安装包（.exe）
- `release/win-unpacked/` - 免安装版本

**自定义打包配置**：

编辑 `package.json` 中的 `build` 字段：

```json
{
  "build": {
    "appId": "com.mikuscat.nanami-assistant",
    "productName": "七海AI助手",
    "directories": {
      "output": "release"
    },
    "win": {
      "target": [
        "nsis",      // 安装包
        "portable"   // 便携版
      ],
      "icon": "public/icon.ico"
    }
  }
}
```

### macOS 平台

```bash
npm run electron:build
```

输出 `.dmg` 和 `.app` 文件。

### Linux 平台

```bash
npm run electron:build
```

输出 `.AppImage` 或 `.deb` 文件。

---

## ⚙️ 配置说明

### 后端 API 地址

编辑 `src/config.ts`：

```typescript
export const API_BASE_URL = process.env.VITE_API_BASE_URL || 'http://localhost:7878'
```

或在项目根目录创建 `.env` 文件：

```bash
VITE_API_BASE_URL=http://your-backend-url:7878
```

### 应用配置

编辑 `electron/main.ts`：

```typescript
const mainWindow = new BrowserWindow({
  width: 1200,           // 窗口宽度
  height: 800,           // 窗口高度
  minWidth: 800,         // 最小宽度
  minHeight: 600,        // 最小高度
  frame: false,          // 无边框（自定义标题栏）
  transparent: false,    // 透明窗口
  // ...
})
```

---

## 📁 项目结构

```
frontend/
├── src/
│   ├── components/              # React 组件
│   │   ├── TitleBar/           # 自定义标题栏
│   │   │   └── index.tsx       # - 窗口控制按钮
│   │   ├── Sidebar/            # 会话侧边栏
│   │   │   └── index.tsx       # - 会话列表、新建对话
│   │   ├── MessageItem/        # 消息项
│   │   │   └── index.tsx       # - 用户/AI 消息展示
│   │   ├── ChatInput/          # 输入框
│   │   │   └── index.tsx       # - 文本输入、文件上传
│   │   ├── TodoList/           # 任务列表
│   │   │   └── index.tsx       # - TODO 展示与操作
│   │   └── Settings/           # 设置面板
│   │       └── index.tsx       # - 主题切换、API 配置
│   │
│   ├── services/               # API 服务层
│   │   └── api.ts             # - 后端通信（流式请求）
│   │
│   ├── store/                  # Zustand 状态管理
│   │   └── chat.ts            # - 聊天状态、会话管理
│   │
│   ├── types/                  # TypeScript 类型定义
│   │   └── index.ts           # - Message、Session、Todo 等
│   │
│   ├── App.tsx                # 主应用组件
│   ├── main.tsx               # React 入口
│   ├── index.css              # 全局样式
│   └── config.ts              # 配置文件
│
├── electron/                   # Electron 主进程
│   ├── main.ts                # - 应用入口、窗口管理
│   └── preload.ts             # - 预加载脚本（IPC 通信）
│
├── public/                     # 静态资源
│   ├── icon.svg               # 应用图标
│   └── icon.ico               # Windows 图标
│
├── package.json               # 项目配置
├── vite.config.ts             # Vite 配置
├── tailwind.config.js         # Tailwind 配置
└── tsconfig.json              # TypeScript 配置
```

---

## 🎨 设计理念

### 简约而不简单

参考 **Cherry Studio** 设计风格，追求：

- ✅ **清晰的视觉层次** - 主次分明的信息结构
- ✅ **流畅的交互动画** - 优雅的过渡效果
- ✅ **优雅的配色方案** - 深色 `#1F2428` / 浅色 `#FCF9F5`
- ✅ **精致的细节处理** - 圆角、阴影、间距

### 配色方案

```css
/* 暗色主题 */
--bg-primary: #1F2428
--bg-secondary: #2D333B
--text-primary: #ADBAC7
--accent: #539BF5

/* 亮色主题 */
--bg-primary: #FCF9F5
--bg-secondary: #FFFFFF
--text-primary: #1F2328
--accent: #0969DA
```

---

## 🔌 IPC 通信

Electron 主进程与渲染进程通过 IPC 通信：

### 预加载脚本（preload.ts）

```typescript
contextBridge.exposeInMainWorld('electron', {
  minimize: () => ipcRenderer.send('window-minimize'),
  maximize: () => ipcRenderer.send('window-maximize'),
  close: () => ipcRenderer.send('window-close'),
})
```

### 主进程（main.ts）

```typescript
ipcMain.on('window-minimize', () => {
  mainWindow.minimize()
})

ipcMain.on('window-maximize', () => {
  if (mainWindow.isMaximized()) {
    mainWindow.unmaximize()
  } else {
    mainWindow.maximize()
  }
})

ipcMain.on('window-close', () => {
  mainWindow.close()
})
```

### 渲染进程（TitleBar 组件）

```typescript
const handleMinimize = () => window.electron.minimize()
const handleMaximize = () => window.electron.maximize()
const handleClose = () => window.electron.close()
```

---

## 📡 API 通信

### 流式请求

使用 Server-Sent Events (SSE) 实现流式响应：

```typescript
// src/services/api.ts
export async function sendMessage(
  input: string,
  sessionId: string,
  onChunk: (chunk: string) => void
) {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    body: formData,
  })

  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const chunk = decoder.decode(value)
    onChunk(chunk)  // 实时回调
  }
}
```

### 文件上传

```typescript
const formData = new FormData()
formData.append('input', message)
formData.append('session_id', sessionId)
formData.append('file', file)  // 可选

await sendMessage(formData)
```

---

## 🐛 常见问题

### Q1: 开发模式下窗口无法打开

**解决方案**：
```bash
# 清除缓存
rm -rf node_modules dist dist-electron
npm install
npm run electron:dev
```

### Q2: 打包后无法连接后端

**原因**：硬编码了 `localhost`

**解决方案**：在设置面板提供 API 地址配置，或使用环境变量：

```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:7878'
```

### Q3: 图标未显示

**解决方案**：
1. 确保 `public/icon.ico` 存在
2. 在 `package.json` 中配置：
```json
{
  "build": {
    "win": {
      "icon": "public/icon.ico"
    }
  }
}
```

---

## 🚀 性能优化

### 1. React 性能优化

```typescript
// 使用 React.memo 避免不必要的重渲染
export const MessageItem = React.memo(({ message }) => {
  // ...
})

// 使用 useMemo 缓存计算结果
const sortedMessages = useMemo(() => {
  return messages.sort((a, b) => a.timestamp - b.timestamp)
}, [messages])
```

### 2. Electron 性能优化

```typescript
// 启用硬件加速
app.commandLine.appendSwitch('enable-gpu-rasterization')

// 预加载窗口
const preloadWindow = new BrowserWindow({
  show: false,
  webPreferences: { preload: './preload.js' }
})
```

---

## 📄 许可证

MIT License

---

<div align="center">

**💙 Built with React + Electron**

[返回主项目](../) | [后端文档](../backend/README.md)

</div>
