// 消息类型
export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  isStreaming?: boolean
}

// 对话类型
export interface Conversation {
  id: string
  title: string
  messages: Message[]
  createdAt: number
  updatedAt: number
}

// TODO类型
export interface Todo {
  id: string
  title: string
  description?: string
  status: 'pending' | 'in_progress' | 'completed'
  order: number
  created_at?: string
  updated_at?: string
}

// 工具调用结果类型
export interface ToolResult {
  tool: string
  error: boolean
  data: any
}

// 主题类型
export type Theme = 'light' | 'dark'

// API响应元信息
export interface MetaInfo {
  compact?: {
    compacted: boolean
    tokens: number
    threshold: number
  }
  ltm_saved?: boolean
  path?: string
  kind?: string
}

// 全局窗口类型扩展(Electron API)
declare global {
  interface Window {
    electronAPI?: {
      getAppVersion: () => Promise<string>
      windowMinimize: () => Promise<void>
      windowMaximize: () => Promise<void>
      windowClose: () => Promise<void>
    }
  }
}
