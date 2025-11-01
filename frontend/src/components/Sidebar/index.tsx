import React, { useState } from 'react'
import { useChatStore } from '../../store/chat'
import { Settings as SettingsComponent } from '../Settings'
import {
  MessageSquare,
  Settings,
  Sun,
  Moon,
  Trash2,
  Save,
  Plus,
  ChevronLeft,
  ChevronRight,
  X,
} from 'lucide-react'

interface SidebarProps {
  onExtractPreferences: () => void
}

export const Sidebar: React.FC<SidebarProps> = ({ onExtractPreferences }) => {
  const {
    theme,
    toggleTheme,
    clearAllConversations,
    messages,
    conversations,
    currentConversationId,
    createConversation,
    deleteConversation,
    switchConversation,
  } = useChatStore()

  const [showHistory, setShowHistory] = useState(false)
  const [showSettings, setShowSettings] = useState(false)

  const handleClearAllChats = () => {
    if (confirm('确定要删除所有历史对话吗？此操作不可恢复！')) {
      clearAllConversations()
    }
  }

  const handleNewChat = () => {
    createConversation()
  }

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffDays = Math.floor(
      (now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24)
    )

    if (diffDays === 0) return '今天'
    if (diffDays === 1) return '昨天'
    if (diffDays < 7) return `${diffDays}天前`
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
  }

  return (
    <>
      {/* 主侧边栏 */}
      <div className="w-16 bg-light-navbar dark:bg-dark-navbar border-r border-gray-200 dark:border-gray-700 flex flex-col items-center py-4 gap-4">
        {/* Logo */}
        <div className="w-10 h-10 rounded-md bg-gradient-to-br from-primary-400 via-primary-500 to-primary-600 flex items-center justify-center shadow-lg">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="white" opacity="0.9">
            <path d="M12 3L3 9l9 6 9-6-9-6zM3 15l9 6 9-6M3 15l9-6" stroke="white" strokeWidth="2" fill="none"/>
          </svg>
        </div>

        <div className="flex-1 flex flex-col gap-3">
          {/* 新建对话 */}
          <button
            onClick={handleNewChat}
            className="p-3 rounded-lg bg-primary-500 hover:bg-primary-600 text-white transition-colors"
            title="新建对话"
          >
            <Plus size={20} />
          </button>

          {/* 对话历史 */}
          <button
            onClick={() => setShowHistory(!showHistory)}
            className={`p-3 rounded-lg transition-colors ${
              showHistory
                ? 'bg-primary-500 text-white'
                : 'hover:bg-light-bg-mute dark:hover:bg-dark-bg-mute'
            }`}
            title="对话历史"
          >
            <MessageSquare size={20} />
          </button>

          {/* 设置 */}
          <button
            onClick={() => setShowSettings(true)}
            className="p-3 rounded-lg hover:bg-light-bg-mute dark:hover:bg-dark-bg-mute transition-colors"
            title="设置"
          >
            <Settings size={20} />
          </button>
        </div>

        {/* 底部操作 */}
        <div className="flex flex-col gap-3">
          {/* 保存偏好 */}
          <button
            onClick={onExtractPreferences}
            disabled={messages.length < 2}
            className="p-3 rounded-lg hover:bg-light-bg-mute dark:hover:bg-dark-bg-mute transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            title="保存偏好"
          >
            <Save size={20} />
          </button>

          {/* 清空所有对话 */}
          <button
            onClick={handleClearAllChats}
            disabled={conversations.length === 0}
            className="p-3 rounded-lg hover:bg-red-500/10 text-red-500 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            title="删除所有历史对话"
          >
            <Trash2 size={20} />
          </button>

          {/* 主题切换 */}
          <button
            onClick={toggleTheme}
            className="p-3 rounded-lg hover:bg-light-bg-mute dark:hover:bg-dark-bg-mute transition-colors"
            title={theme === 'dark' ? '切换到浅色模式' : '切换到深色模式'}
          >
            {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
          </button>
        </div>
      </div>

      {/* 对话历史面板 */}
      {showHistory && (
        <div className="w-64 bg-light-bg-soft dark:bg-dark-bg-soft border-r border-gray-200 dark:border-gray-700 flex flex-col">
          {/* 头部 */}
          <div className="h-12 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between px-4">
            <h2 className="font-semibold text-sm">对话历史</h2>
            <button
              onClick={() => setShowHistory(false)}
              className="p-1 rounded hover:bg-light-bg-mute dark:hover:bg-dark-bg-mute"
            >
              <ChevronLeft size={16} />
            </button>
          </div>

          {/* 对话列表 */}
          <div className="flex-1 overflow-y-auto p-2">
            {conversations.length === 0 ? (
              <div className="text-center py-8 text-sm opacity-50">
                暂无对话历史
              </div>
            ) : (
              conversations.map((conv) => (
                <div
                  key={conv.id}
                  className={`group relative mb-2 p-3 rounded-lg cursor-pointer transition-colors ${
                    conv.id === currentConversationId
                      ? 'bg-primary-500 text-white'
                      : 'hover:bg-light-bg-mute dark:hover:bg-dark-bg-mute'
                  }`}
                  onClick={() => switchConversation(conv.id)}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate">
                        {conv.title}
                      </div>
                      <div
                        className={`text-xs mt-1 ${
                          conv.id === currentConversationId
                            ? 'opacity-80'
                            : 'opacity-50'
                        }`}
                      >
                        {formatTime(conv.updatedAt)}
                      </div>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        if (confirm('确定删除这个对话吗？'))
                          deleteConversation(conv.id)
                      }}
                      className={`opacity-0 group-hover:opacity-100 p-1 rounded transition-opacity ${
                        conv.id === currentConversationId
                          ? 'hover:bg-white/20'
                          : 'hover:bg-red-500/10 text-red-500'
                      }`}
                    >
                      <X size={14} />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {showSettings && <SettingsComponent onClose={() => setShowSettings(false)} />}
    </>
  )
}
