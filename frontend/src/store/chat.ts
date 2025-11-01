import { create } from 'zustand'
import { Message, Todo, Theme, Conversation } from '../types'

interface ChatState {
  conversations: Conversation[]
  currentConversationId: string | null
  createConversation: () => void
  deleteConversation: (id: string) => void
  switchConversation: (id: string) => void
  updateConversationTitle: (id: string, title: string) => void
  clearAllConversations: () => void

  messages: Message[]
  addMessage: (message: Message) => void
  updateMessage: (id: string, content: string) => void
  deleteMessage: (id: string) => void
  deleteMessagesAfter: (id: string) => void
  clearMessages: () => void

  todos: Todo[]
  setTodos: (todos: Todo[]) => void

  theme: Theme
  toggleTheme: () => void

  isLoading: boolean
  setLoading: (loading: boolean) => void

  inputText: string
  setInputText: (text: string) => void
}

const generateTitle = (firstMessage: string): string => {
  return firstMessage.slice(0, 30) + (firstMessage.length > 30 ? '...' : '')
}

// 从localStorage加载初始状态
const loadInitialState = () => {
  try {
    const saved = localStorage.getItem('nanami-chat-storage')
    if (saved) {
      const parsed = JSON.parse(saved)
      return {
        conversations: parsed.conversations || [],
        currentConversationId: parsed.currentConversationId || null,
        theme: parsed.theme || 'light',
      }
    }
  } catch (error) {
    console.error('Failed to load state:', error)
  }
  return {
    conversations: [],
    currentConversationId: null,
    theme: 'light' as Theme,
  }
}

// 保存状态到localStorage
const saveState = (state: ChatState) => {
  try {
    localStorage.setItem(
      'nanami-chat-storage',
      JSON.stringify({
        conversations: state.conversations,
        currentConversationId: state.currentConversationId,
        theme: state.theme,
      })
    )
  } catch (error) {
    console.error('Failed to save state:', error)
  }
}

const initialState = loadInitialState()

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: initialState.conversations,
  currentConversationId: initialState.currentConversationId,

  createConversation: () => {
    const newConv: Conversation = {
      id: `conv-${Date.now()}`,
      title: '新对话',
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    }
    set((state) => {
      const newState = {
        conversations: [newConv, ...state.conversations],
        currentConversationId: newConv.id,
        messages: [],
        todos: [],
      }
      saveState({ ...state, ...newState })
      return newState
    })
  },

  deleteConversation: (id) => {
    const state = get()
    const newConversations = state.conversations.filter((c) => c.id !== id)
    const isCurrentDeleted = state.currentConversationId === id

    if (isCurrentDeleted) {
      const nextConv = newConversations[0]
      const newState = {
        conversations: newConversations,
        currentConversationId: nextConv?.id || null,
        messages: nextConv?.messages || [],
      }
      set(newState)
      saveState({ ...state, ...newState })
    } else {
      set({ conversations: newConversations })
      saveState({ ...state, conversations: newConversations })
    }
  },

  switchConversation: (id) => {
    const state = get()
    const conv = state.conversations.find((c) => c.id === id)
    if (conv) {
      const newState = {
        currentConversationId: id,
        messages: conv.messages,
        todos: [],
      }
      set(newState)
      saveState({ ...state, ...newState })
    }
  },

  updateConversationTitle: (id, title) => {
    set((state) => {
      const conversations = state.conversations.map((c) =>
        c.id === id ? { ...c, title, updatedAt: Date.now() } : c
      )
      const newState = { conversations }
      saveState({ ...state, ...newState })
      return newState
    })
  },

  messages: [],
  addMessage: (message) => {
    set((state) => {
      const newMessages = [...state.messages, message]
      const convId = state.currentConversationId

      if (convId) {
        const conversations = state.conversations.map((c) => {
          if (c.id === convId) {
            const title =
              c.messages.length === 0 && message.role === 'user'
                ? generateTitle(message.content)
                : c.title
            return {
              ...c,
              title,
              messages: newMessages,
              updatedAt: Date.now(),
            }
          }
          return c
        })
        const newState = { messages: newMessages, conversations }
        saveState({ ...state, ...newState })
        return newState
      }

      return { messages: newMessages }
    })
  },

  updateMessage: (id, content) => {
    set((state) => {
      const newMessages = state.messages.map((msg) =>
        msg.id === id ? { ...msg, content, isStreaming: false } : msg
      )
      const convId = state.currentConversationId

      if (convId) {
        const conversations = state.conversations.map((c) =>
          c.id === convId
            ? { ...c, messages: newMessages, updatedAt: Date.now() }
            : c
        )
        const newState = { messages: newMessages, conversations }
        saveState({ ...state, ...newState })
        return newState
      }

      return { messages: newMessages }
    })
  },

  deleteMessage: (id) => {
    set((state) => {
      const newMessages = state.messages.filter((msg) => msg.id !== id)
      const convId = state.currentConversationId

      if (convId) {
        const conversations = state.conversations.map((c) =>
          c.id === convId
            ? { ...c, messages: newMessages, updatedAt: Date.now() }
            : c
        )
        const newState = { messages: newMessages, conversations }
        saveState({ ...state, ...newState })
        return newState
      }

      return { messages: newMessages }
    })
  },

  deleteMessagesAfter: (id) => {
    set((state) => {
      const messageIndex = state.messages.findIndex((msg) => msg.id === id)
      if (messageIndex === -1) return state

      const newMessages = state.messages.slice(0, messageIndex)
      const convId = state.currentConversationId

      if (convId) {
        const conversations = state.conversations.map((c) =>
          c.id === convId
            ? { ...c, messages: newMessages, updatedAt: Date.now() }
            : c
        )
        const newState = { messages: newMessages, conversations }
        saveState({ ...state, ...newState })
        return newState
      }

      return { messages: newMessages }
    })
  },

  clearMessages: () => {
    const state = get()
    if (state.currentConversationId) {
      const newState = {
        conversations: state.conversations.filter(
          (c) => c.id !== state.currentConversationId
        ),
        currentConversationId: null,
        messages: [],
        todos: [],
      }
      set(newState)
      saveState({ ...state, ...newState })
    }
  },

  clearAllConversations: () => {
    const state = get()
    const newState = {
      conversations: [],
      currentConversationId: null,
      messages: [],
      todos: [],
    }
    set(newState)
    saveState({ ...state, ...newState })
  },

  todos: [],
  setTodos: (todos) => set({ todos }),

  theme: initialState.theme,
  toggleTheme: () => {
    set((state) => {
      const newTheme = state.theme === 'dark' ? 'light' : 'dark'
      document.documentElement.classList.toggle('dark', newTheme === 'dark')
      const newState = { theme: newTheme }
      saveState({ ...state, ...newState })
      return newState
    })
  },

  isLoading: false,
  setLoading: (loading) => set({ isLoading: loading }),

  inputText: '',
  setInputText: (text) => set({ inputText: text }),
}))
