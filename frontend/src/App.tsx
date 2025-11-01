import React, { useEffect, useRef, useState } from 'react'
import { useChatStore } from './store/chat'
import { TitleBar } from './components/TitleBar'
import { Sidebar } from './components/Sidebar'
import { MessageItem } from './components/MessageItem'
import { ChatInput } from './components/ChatInput'
import { TodoList } from './components/TodoList'
import { streamChat, extractPreferences, generateTitle, fetchTodos, updateTodoStatus, subscribeTodoStream } from './services/api'
import { Message, Todo } from './types'
import { AlertCircle } from 'lucide-react'

function App() {
  const {
    messages,
    addMessage,
    updateMessage,
    deleteMessagesAfter,
    todos,
    setTodos,
    isLoading,
    setLoading,
    theme,
    currentConversationId,
    createConversation,
    updateConversationTitle,
    conversations,
  } = useChatStore()

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // 初始化：确保有一个对话
  useEffect(() => {
    if (!currentConversationId) {
      createConversation()
    }
  }, [])

  // 初始化主题
  useEffect(() => {
    // 确保DOM和theme状态同步
    if (theme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [theme])

  // 自动滚动到底部
  useEffect(() => {
    if (messagesEndRef.current) {
      const container = messagesEndRef.current.parentElement
      if (container) {
        container.scrollTop = container.scrollHeight
      }
    }
  }, [messages])

  // 会话切换时，主动拉取该会话的TODO列表
  useEffect(() => {
    (async () => {
      if (currentConversationId) {
        try {
          const list = await fetchTodos(currentConversationId)
          setTodos(list)
        } catch {
          setTodos([])
        }
      } else {
        setTodos([])
      }
    })()
  }, [currentConversationId])

  // SSE订阅：实时接收TODO更新（优雅、低侵入）
  useEffect(() => {
    if (!currentConversationId) return
    const sub = subscribeTodoStream(currentConversationId, (list) => setTodos(list))
    return () => sub.close()
  }, [currentConversationId])

  // 发送消息
  const handleSendMessage = async (text: string, files?: File[]) => {
    if (!text.trim() && (!files || files.length === 0)) return

    setError(null)
    setLoading(true)

    // 创建新的 AbortController
    const abortController = new AbortController()
    abortControllerRef.current = abortController

    // 添加用户消息
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: Date.now(),
    }
    addMessage(userMessage)

    // 创建助手消息
    const assistantId = `assistant-${Date.now()}`
    const assistantMessage: Message = {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      isStreaming: true,
    }
    addMessage(assistantMessage)

    try {
      let accumulatedContent = ''

      // 流式接收响应（传入历史消息、会话ID和 abort signal）
      // 核心修改：传递 currentConversationId 作为 session_id，实现对话窗口级别的上下文持久化
      for await (const chunk of streamChat(
        text,
        files,
        messages,
        currentConversationId || undefined,  // 传递当前对话窗口ID作为session_id
        abortController.signal
      )) {
        if (chunk.type === 'text') {
          // 文本内容,累加到助手消息
          accumulatedContent += chunk.content
          updateMessage(assistantId, accumulatedContent)
        } else if (chunk.type === 'tool' && chunk.data) {
          // 工具调用结果
          const toolResult = chunk.data
          const toolName = toolResult.tool

          // 统一处理：只要返回 data.todos 就整体刷新
          if (toolResult.data?.todos) {
            setTodos(toolResult.data.todos)
          } else if (
            toolName === 'create_todo' ||
            toolName === 'update_todo' ||
            toolName === 'list_todos' ||
            toolName === 'get_todos' || // 兼容历史命名
            toolName === 'create_subagent_todo' ||
            toolName === 'update_subagent_todo'
          ) {
            if (toolResult.data?.todo) {
              // 追加/更新单条
              const item = toolResult.data.todo as Todo
              const exists = todos.findIndex((t) => t.id === item.id)
              if (exists >= 0) {
                const next = [...todos]
                next[exists] = item
                setTodos(next)
              } else {
                setTodos([...todos, item])
              }
            }
          }

          // 子代理执行结束后，主动刷新当前会话的TODO（SubAgent内部已持久化）
          if (toolName.endsWith('_subagent') && currentConversationId) {
            try {
              const list = await fetchTodos(currentConversationId)
              setTodos(list)
            } catch {}
          }
        }
      }

      // 完成流式传输，标记为非流式
      updateMessage(assistantId, accumulatedContent)
      if (currentConversationId) {
        try {
          const list = await fetchTodos(currentConversationId)
          setTodos(list)
        } catch {}
      }

      // 生成标题（仅在首次对话时）
      if (currentConversationId) {
        const currentConv = conversations.find((c) => c.id === currentConversationId)
        if (currentConv && currentConv.title === '新对话' && currentConv.messages.length <= 2) {
          const allMessages = [...messages, userMessage, { ...assistantMessage, content: accumulatedContent }]
          const title = await generateTitle(allMessages)
          if (title) {
            updateConversationTitle(currentConversationId, title)
          }
        }
      }
    } catch (err) {
      // 检查是否是用户主动中断
      if (err instanceof Error && err.name === 'AbortError') {
        updateMessage(assistantId, accumulatedContent || '（已中断）')
        setError('已中断当前请求')
      } else {
        console.error('发送消息失败:', err)
        setError(err instanceof Error ? err.message : '发送失败')
        updateMessage(assistantId, '抱歉,发生了错误,请稍后重试。')
      }
    } finally {
      setLoading(false)
      abortControllerRef.current = null
    }
  }

  // 中断当前请求
  const handleAbort = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
  }

  // 提取偏好
  const handleExtractPreferences = async () => {
    if (messages.length < 2) {
      alert('对话消息过少,无法提取偏好')
      return
    }

    try {
      const result = await extractPreferences(messages)
      if (result.success) {
        alert(
          `✅ 偏好已保存!\n\n${result.preferences}\n\n保存路径: ${result.path}`
        )
      } else {
        alert(`❌ 提取失败: ${result.error}`)
      }
    } catch (err) {
      alert(`❌ 网络错误: ${err instanceof Error ? err.message : '未知错误'}`)
    }
  }

  const handleRegenerate = async (message: Message) => {
    deleteMessagesAfter(message.id)

    await new Promise(resolve => setTimeout(resolve, 100))

    await handleSendMessage(message.content)
  }

  return (
    <div className="flex flex-col h-full bg-light-bg dark:bg-dark-bg text-gray-900 dark:text-gray-100">
      {/* 自定义标题栏 */}
      <TitleBar />

      <div className="flex flex-1 overflow-hidden">
        {/* 侧边栏 */}
        <Sidebar onExtractPreferences={handleExtractPreferences} />

        {/* 主内容区 */}
        <div className="flex-1 flex flex-col">
          {/* 消息区域 */}
          <div className="flex-1 overflow-y-auto px-6 py-4">
          {/* 欢迎消息 */}
          {messages.length === 0 && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <h2 className="text-2xl font-bold mb-2">你好!我是七海</h2>
                <p className="text-sm opacity-60">
                  一个优雅的AI助手,随时为你提供帮助
                </p>
              </div>
            </div>
          )}

          {/* TODO列表 */}
          {todos.length > 0 && (
            <TodoList
              todos={todos}
              onToggle={async (todo) => {
                if (!currentConversationId) return
                try {
                  const next = todo.status === 'completed' ? 'pending' : 'completed'
                  const updated = await updateTodoStatus(todo.id, next, currentConversationId)
                  const idx = todos.findIndex((t) => t.id === todo.id)
                  if (idx >= 0) {
                    const cp = [...todos]
                    cp[idx] = updated
                    setTodos(cp)
                  }
                } catch {}
              }}
            />
          )}

          {/* 消息列表 */}
          {messages.map((message) => (
            <MessageItem
              key={message.id}
              message={message}
              onRegenerate={handleRegenerate}
            />
          ))}

          {/* 错误提示 */}
          {error && (
            <div className="mb-4 p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-3 text-red-600 dark:text-red-400">
              <AlertCircle size={20} />
              <span className="text-sm">{error}</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* 输入区域 */}
        <ChatInput onSend={handleSendMessage} onAbort={handleAbort} disabled={isLoading} />
      </div>
    </div>
    </div>
  )
}

export default App
