import { Message, ToolResult, MetaInfo, Todo } from '../types'
import { config } from '../config'

const API_BASE_URL = config.apiBaseUrl

// 流式聊天接口
export async function* streamChat(
  input: string,
  files?: File[],
  historyMessages?: Message[],
  sessionId?: string,  // 会话ID，用于后端TODO和记忆隔离
  signal?: AbortSignal
): AsyncGenerator<{
  type: 'text' | 'tool' | 'meta'
  content: string
  data?: ToolResult | MetaInfo
}> {
  const formData = new FormData()
  formData.append('input', input)

  // 传递会话ID（核心修改：实现对话窗口级别的session持久化）
  if (sessionId) {
    formData.append('session_id', sessionId)
  }

  if (files && files.length > 0) {
    files.forEach((file) => {
      formData.append('files', file)
    })
  }

  // 发送历史消息（最近10轮对话，避免上下文过长）
  if (historyMessages && historyMessages.length > 0) {
    // 只取最近20条消息（10轮对话）
    const recentMessages = historyMessages.slice(-20).map(msg => ({
      role: msg.role,
      content: msg.content
    }))
    formData.append('messages', JSON.stringify(recentMessages))
  }

  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    body: formData,
    signal: signal
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }

  const reader = response.body!.getReader()
  const decoder = new TextDecoder()

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value, { stream: true })

      // 解析不同类型的消息
      if (chunk.includes('[meta]')) {
        // 元信息
        const match = chunk.match(/\[meta\]\s*(.+)/)
        if (match) {
          try {
            const meta = JSON.parse(match[1].replace(/'/g, '"'))
            yield { type: 'meta', content: chunk, data: meta }
          } catch {
            yield { type: 'meta', content: chunk }
          }
        }
      } else if (chunk.includes('[🔧')) {
        // 工具调用通知
        yield { type: 'tool', content: chunk }
      } else if (chunk.includes('[✓')) {
        // 工具执行结果
        const match = chunk.match(/\[✓\s+(\w+)\]:\s*(.+)/)
        if (match) {
          try {
            const toolResult: ToolResult = {
              tool: match[1],
              error: false,
              data: JSON.parse(match[2]),
            }
            yield { type: 'tool', content: chunk, data: toolResult }
          } catch {
            yield { type: 'tool', content: chunk }
          }
        }
      } else if (chunk.trim()) {
        // 文本内容
        yield { type: 'text', content: chunk }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

// 列出指定会话的TODO列表
export async function fetchTodos(sessionId: string): Promise<Todo[]> {
  const res = await fetch(`${API_BASE_URL}/todos?session_id=${encodeURIComponent(sessionId)}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return (await res.json()) as Todo[]
}

// 订阅指定会话的TODO SSE流
export function subscribeTodoStream(
  sessionId: string,
  onUpdate: (todos: Todo[]) => void
) {
  const url = `${API_BASE_URL}/todos/stream?session_id=${encodeURIComponent(sessionId)}`
  let es: EventSource | null = null
  try {
    es = new EventSource(url)

    const handle = (dataText: string) => {
      try {
        const payload = JSON.parse(dataText)
        const list: Todo[] = payload.todos || payload || []
        if (Array.isArray(list)) onUpdate(list)
      } catch {}
    }

    es.addEventListener('todos', (ev: MessageEvent) => handle(ev.data))
    es.onmessage = (ev) => handle(ev.data)
    es.onerror = () => {
      // 出错时关闭，让上层按需回退
      try { es?.close() } catch {}
    }
  } catch {
    // 忽略，调用方可回退到轮询
  }

  return {
    close: () => { try { es?.close() } catch {} }
  }
}

// 更新指定TODO状态/内容（最常见：标记完成）
export async function updateTodoStatus(
  todoId: string,
  status: 'pending' | 'in_progress' | 'completed',
  sessionId: string
): Promise<Todo> {
  const res = await fetch(`${API_BASE_URL}/todos/${encodeURIComponent(todoId)}?session_id=${encodeURIComponent(sessionId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status })
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return (await res.json()) as Todo
}

// 提取用户偏好
export async function extractPreferences(messages: Message[]) {
  const response = await fetch(`${API_BASE_URL}/extract_preferences`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      messages: messages.map((msg) => ({
        role: msg.role,
        content: msg.content,
      })),
    }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.error || '提取偏好失败')
  }

  return await response.json()
}

// OpenAI兼容接口
export async function chatCompletion(messages: Message[]) {
  const response = await fetch(`${API_BASE_URL}/v1/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: 'gpt-4',
      messages: messages.map((msg) => ({
        role: msg.role,
        content: msg.content,
      })),
    }),
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  return await response.json()
}

// 生成对话标题
export async function generateTitle(messages: Message[]): Promise<string | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/generate_title`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(
        messages.map((msg) => ({
          role: msg.role,
          content: msg.content,
        }))
      ),
    })

    if (!response.ok) {
      console.error('标题生成失败:', response.statusText)
      return null
    }

    const result = await response.json()
    return result.title || null
  } catch (error) {
    console.error('标题生成错误:', error)
    return null
  }
}

// 获取模型列表（OpenAI兼容格式）
export async function fetchModels(): Promise<{id: string, object: string}[]> {
  const response = await fetch(`${API_BASE_URL}/v1/models`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `获取模型列表失败: HTTP ${response.status}`)
  }

  const data = await response.json()
  return data.data || []
}

